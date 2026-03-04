"""
Case-level orchestrator.

Inspects which document types are uploaded for a case and fires off
all applicable processing pipelines in parallel. Each pipeline
independently updates its own pipeline_status in MongoDB.

Risk analysis is triggered automatically when MER and/or pathology
extraction completes, using atomic MongoDB operations to prevent
duplicate triggers.
"""

import asyncio
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List

from bson import ObjectId
from pymongo import ReturnDocument

from app.dependencies import get_database
from app.config import settings
from app.services.mer.processor import process_mer
from app.services.pathology.processor import process_pathology
from app.services.risk.processor import process_risk
from app.services.face_match.processor import process_face_match as process_face_match_v1
from app.services.face_match_v2.processor import process_face_match_v2
from app.services.location_check.processor import process_location_check
from app.services.task_queue import enqueue_task


def _get_face_match_processor():
    """Get the face match processor based on config."""
    if settings.face_match_algorithm == "v2":
        return process_face_match_v2
    return process_face_match_v1

logger = logging.getLogger(__name__)


# ─── Pipeline runners ────────────────────────────────────────────────────────
# Each runner:
#   1. Sets pipeline_status.X = "processing"
#   2. Runs the pipeline
#   3. Sets pipeline_status.X = "extracted" on success, "failed" on error
#   4. Returns a result dict

async def _update_pipeline_status(
    case_id: str,
    pipeline: str,
    stage: str,
    error_message: str = None,
    error_traceback: str = None,
):
    """Update pipeline status and optionally set/clear pipeline error."""
    db = await get_database()
    set_op = {f"pipeline_status.{pipeline}": stage, "updated_at": datetime.utcnow()}
    if stage == "failed" and error_message is not None:
        set_op[f"pipeline_errors.{pipeline}"] = {
            "message": error_message,
            "traceback": error_traceback or "",
        }
    update = {"$set": set_op}
    if stage != "failed":
        update["$unset"] = {f"pipeline_errors.{pipeline}": 1}
    await db.cases.update_one({"_id": ObjectId(case_id)}, update)


async def _run_mer(case_id: str, mer_files: List[dict]) -> Dict[str, Any]:
    """Run MER pipeline with status tracking."""
    await _update_pipeline_status(case_id, "mer", "processing")
    try:
        result = await process_mer(case_id, mer_files)
        await _update_pipeline_status(case_id, "mer", "extracted")

        # Trigger risk analysis if conditions are met
        await _maybe_trigger_risk(case_id)

        # Trigger test verification if both MER and pathology are done
        await _maybe_trigger_test_verification(case_id)

        return {"pipeline": "mer", "status": "extracted", "result": result}
    except Exception as e:
        await _update_pipeline_status(
            case_id, "mer", "failed",
            error_message=str(e), error_traceback=traceback.format_exc(),
        )
        return {"pipeline": "mer", "status": "failed", "error": str(e), "traceback": traceback.format_exc()}


async def _run_pathology(case_id: str, path_files: List[dict]) -> Dict[str, Any]:
    """Run pathology pipeline with status tracking."""
    await _update_pipeline_status(case_id, "pathology", "processing")
    try:
        result = await process_pathology(case_id, path_files)
        await _update_pipeline_status(case_id, "pathology", "extracted")

        # Trigger risk analysis if conditions are met
        await _maybe_trigger_risk(case_id)

        # Trigger location check (needs pathology OCR for lab address)
        await _maybe_trigger_location_check(case_id)

        # Trigger test verification if both MER and pathology are done
        await _maybe_trigger_test_verification(case_id)

        return {"pipeline": "pathology", "status": "extracted", "result": result}
    except Exception as e:
        await _update_pipeline_status(
            case_id, "pathology", "failed",
            error_message=str(e), error_traceback=traceback.format_exc(),
        )
        return {"pipeline": "pathology", "status": "failed", "error": str(e), "traceback": traceback.format_exc()}


async def _run_face_match(case_id: str, photo_files: List[dict], id_files: List[dict]) -> Dict[str, Any]:
    """Run face matching pipeline with status tracking."""
    await _update_pipeline_status(case_id, "face_match", "processing")
    try:
        process_face_match = _get_face_match_processor()
        result = await process_face_match(case_id, photo_files, id_files)
        await _update_pipeline_status(case_id, "face_match", "extracted")
        return {"pipeline": "face_match", "status": "extracted", "result": result}
    except Exception as e:
        await _update_pipeline_status(
            case_id, "face_match", "failed",
            error_message=str(e), error_traceback=traceback.format_exc(),
        )
        return {"pipeline": "face_match", "status": "failed", "error": str(e), "traceback": traceback.format_exc()}


async def _run_location_check(
    case_id: str,
    photo_files: List[dict],
    id_files: List[dict],
) -> Dict[str, Any]:
    """Run location check pipeline with status tracking."""
    await _update_pipeline_status(case_id, "location_check", "processing")
    try:
        result = await process_location_check(case_id, photo_files, id_files)
        await _update_pipeline_status(case_id, "location_check", "extracted")
        return {"pipeline": "location_check", "status": "extracted", "result": result}
    except Exception as e:
        await _update_pipeline_status(
            case_id, "location_check", "failed",
            error_message=str(e), error_traceback=traceback.format_exc(),
        )
        return {"pipeline": "location_check", "status": "failed", "error": str(e), "traceback": traceback.format_exc()}


async def _run_risk(case_id: str) -> Dict[str, Any]:
    """Run risk analysis pipeline with status tracking."""
    # Status is already set to "processing" by _maybe_trigger_risk
    try:
        result = await process_risk(case_id)
        await _update_pipeline_status(case_id, "risk", "extracted")
        return {"pipeline": "risk", "status": "extracted", "result": result}
    except Exception as e:
        await _update_pipeline_status(
            case_id, "risk", "failed",
            error_message=str(e), error_traceback=traceback.format_exc(),
        )
        logger.error(f"Risk analysis failed for case {case_id}: {e}")
        return {"pipeline": "risk", "status": "failed", "error": str(e), "traceback": traceback.format_exc()}


async def _maybe_trigger_risk(case_id: str):
    """
    Trigger risk analysis if conditions are met.

    Conditions:
    - MER extracted AND (pathology extracted OR pathology not uploaded)
    - OR pathology extracted AND (MER extracted OR MER not uploaded)

    Uses atomic MongoDB update to prevent duplicate triggers when
    both MER and pathology complete near-simultaneously.
    """
    db = await get_database()

    # Get current case state
    case = await db.cases.find_one({"_id": ObjectId(case_id)})
    if not case:
        logger.error(f"Case {case_id} not found for risk trigger check")
        return

    pipeline_status = case.get("pipeline_status", {})
    documents = case.get("documents", {})

    mer_status = pipeline_status.get("mer", "not_started")
    path_status = pipeline_status.get("pathology", "not_started")
    risk_status = pipeline_status.get("risk", "not_started")

    mer_uploaded = bool(documents.get("mer"))
    path_uploaded = bool(documents.get("pathology"))

    mer_ready = mer_status in ("extracted", "reviewed")
    path_ready = path_status in ("extracted", "reviewed")

    # Determine if risk should trigger
    # Case 1: MER ready and (pathology ready OR pathology not uploaded)
    # Case 2: Pathology ready and (MER ready OR MER not uploaded)
    should_trigger = (
        (mer_ready and (path_ready or not path_uploaded))
        or (path_ready and (mer_ready or not mer_uploaded))
    )

    if not should_trigger:
        logger.info(
            f"Risk analysis not triggered for case {case_id}: "
            f"mer={mer_status}, path={path_status}, "
            f"mer_uploaded={mer_uploaded}, path_uploaded={path_uploaded}"
        )
        return

    # Skip if already processing or completed
    if risk_status in ("processing", "extracted", "reviewed"):
        logger.info(
            f"Risk analysis already {risk_status} for case {case_id}, skipping"
        )
        return

    # Atomic: set risk status to "processing" only if not already processing/done
    result = await db.cases.find_one_and_update(
        {
            "_id": ObjectId(case_id),
            "pipeline_status.risk": {"$in": ["not_started", "failed"]},
        },
        {
            "$set": {
                "pipeline_status.risk": "processing",
                "updated_at": datetime.utcnow(),
            }
        },
        return_document=ReturnDocument.AFTER,
    )

    if result:
        logger.info(f"Enqueuing risk analysis for case {case_id}")
        await enqueue_task(case_id, "risk")
    else:
        logger.info(
            f"Risk analysis trigger race lost for case {case_id}, "
            "another process is handling it"
        )


async def _run_test_verification(case_id: str) -> Dict[str, Any]:
    """Run test verification Phase 2 (compare requirements vs pathology)."""
    try:
        from app.services.test_verification.processor import complete_verification
        result = await complete_verification(case_id)
        return {"pipeline": "test_verification", "status": "extracted", "result": result}
    except Exception as e:
        await _update_pipeline_status(
            case_id, "test_verification", "failed",
            error_message=str(e), error_traceback=traceback.format_exc(),
        )
        logger.error(f"Test verification failed for case {case_id}: {e}")
        return {"pipeline": "test_verification", "status": "failed", "error": str(e)}


async def _maybe_trigger_test_verification(case_id: str):
    """
    Trigger test verification once both MER and pathology have completed.

    The requirements extraction (Phase 1) happens inside MER processing.
    This function triggers Phase 2 — comparing those requirements against
    pathology results — only when both pipelines are done.
    """
    db = await get_database()

    case = await db.cases.find_one({"_id": ObjectId(case_id)})
    if not case:
        logger.error(f"Case {case_id} not found for test verification trigger")
        return

    pipeline_status = case.get("pipeline_status", {})
    documents = case.get("documents", {})

    mer_status = pipeline_status.get("mer", "not_started")
    path_status = pipeline_status.get("pathology", "not_started")
    tv_status = pipeline_status.get("test_verification", "not_started")

    path_uploaded = bool(documents.get("pathology"))

    mer_ready = mer_status in ("extracted", "reviewed")
    path_ready = path_status in ("extracted", "reviewed")

    # MER must be ready (it does the extraction). Pathology must be ready
    # OR not uploaded (if no pathology, tests just won't match).
    if not (mer_ready and (path_ready or not path_uploaded)):
        logger.info(
            f"Test verification not triggered for case {case_id}: "
            f"mer={mer_status}, path={path_status}, path_uploaded={path_uploaded}"
        )
        return

    # Only trigger if extraction happened (status == pending_verification)
    if tv_status != "pending_verification":
        logger.info(
            f"Test verification skipped for case {case_id}: "
            f"tv_status={tv_status} (not pending_verification)"
        )
        return

    logger.info(f"Enqueuing test_verification for case {case_id}")
    await enqueue_task(case_id, "test_verification")


async def _maybe_trigger_location_check(case_id: str):
    """
    Trigger location check after pathology extraction completes.

    Location check depends on pathology OCR for lab address extraction,
    so it must run AFTER pathology extraction (not in parallel).

    Requires at least one of: photo or id_proof uploaded.
    """
    db = await get_database()

    # Get current case state
    case = await db.cases.find_one({"_id": ObjectId(case_id)})
    if not case:
        logger.error(f"Case {case_id} not found for location check trigger")
        return

    pipeline_status = case.get("pipeline_status", {})
    documents = case.get("documents", {})
    location_status = pipeline_status.get("location_check", "not_started")

    # Check if we have required documents
    photo_files = _get_uploaded_files(case, "photo")
    id_files = _get_uploaded_files(case, "id_proof")

    if not photo_files and not id_files:
        logger.info(
            f"Location check not triggered for case {case_id}: "
            "no photo or id_proof uploaded"
        )
        return

    # Skip if already processing or completed
    if location_status in ("processing", "extracted", "reviewed"):
        logger.info(
            f"Location check already {location_status} for case {case_id}, skipping"
        )
        return

    # Atomic: set location_check status to "processing" only if not already processing/done
    result = await db.cases.find_one_and_update(
        {
            "_id": ObjectId(case_id),
            "pipeline_status.location_check": {"$in": ["not_started", "failed"]},
        },
        {
            "$set": {
                "pipeline_status.location_check": "processing",
                "updated_at": datetime.utcnow(),
            }
        },
        return_document=ReturnDocument.AFTER,
    )

    if result:
        logger.info(f"Enqueuing location check for case {case_id}")
        await enqueue_task(case_id, "location_check")
    else:
        logger.info(
            f"Location check trigger race lost for case {case_id}, "
            "another process is handling it"
        )


# ─── Helpers ─────────────────────────────────────────────────────────────────

# Pipelines in these states are considered "done" and won't be re-triggered
_COMPLETED_STATES = {"extracted", "reviewed"}

# Only pipelines in these states will be (re-)triggered
_RUNNABLE_STATES = {"not_started", "failed"}


def _get_uploaded_files(case: dict, doc_type: str) -> List[dict]:
    """Extract uploaded files of a given document type from a case."""
    files = case.get("documents", {}).get(doc_type, [])
    return [f for f in files if f.get("status") == "uploaded"]


def _should_run(pipeline_status: Dict[str, str], pipeline: str) -> bool:
    """Check if a pipeline should run based on its current status."""
    current = pipeline_status.get(pipeline, "not_started")
    return current in _RUNNABLE_STATES


async def _is_risk_stale(case_id: str) -> bool:
    """
    Check if risk result used older MER/pathology versions than currently available.

    Returns True if risk should re-run because MER or pathology has been updated
    (e.g., user edited and saved new version) since risk was last computed.
    """
    db = await get_database()

    # Get latest risk result
    risk = await db.risk_results.find_one(
        {"case_id": case_id},
        sort=[("version", -1)],
        projection={"mer_version": 1, "pathology_version": 1},
    )
    if not risk:
        return False  # No risk result → not "stale", just not_started

    # Get latest MER version
    mer = await db.mer_results.find_one(
        {"case_id": case_id},
        sort=[("version", -1)],
        projection={"version": 1},
    )
    # Get latest pathology version
    path = await db.pathology_results.find_one(
        {"case_id": case_id},
        sort=[("version", -1)],
        projection={"version": 1},
    )

    latest_mer = mer.get("version") if mer else None
    latest_path = path.get("version") if path else None

    risk_mer = risk.get("mer_version")
    risk_path = risk.get("pathology_version")

    # Stale if either version differs (when both exist)
    mer_stale = latest_mer is not None and latest_mer != risk_mer
    path_stale = latest_path is not None and latest_path != risk_path

    if mer_stale or path_stale:
        logger.info(
            f"Risk is stale for case {case_id}: "
            f"MER v{risk_mer}→v{latest_mer}, Path v{risk_path}→v{latest_path}"
        )
        return True

    return False


# ─── Main orchestrator ───────────────────────────────────────────────────────

async def get_pipelines_to_trigger(case_id: str, case: dict) -> tuple[List[str], List[str]]:
    """
    Determine which pipelines will be triggered without actually running them.

    Auto-triggered pipelines (not part of initial parallel run):
    - Risk analysis: auto-triggers after MER/pathology extraction
    - Location check: auto-triggers after pathology extraction (needs lab OCR)

    Returns:
        (pipelines_triggered, pipelines_skipped)
    """
    pipeline_status = case.get("pipeline_status", {})
    mer_files = _get_uploaded_files(case, "mer")
    path_files = _get_uploaded_files(case, "pathology")
    photo_files = _get_uploaded_files(case, "photo")
    id_files = _get_uploaded_files(case, "id_proof")

    triggered = []
    skipped = []

    if mer_files and _should_run(pipeline_status, "mer"):
        triggered.append("mer")
    else:
        skipped.append("mer")

    if path_files and _should_run(pipeline_status, "pathology"):
        triggered.append("pathology")
    else:
        skipped.append("pathology")

    # Risk: check if stale (input versions changed since last run)
    risk_status = pipeline_status.get("risk", "not_started")
    mer_ready = pipeline_status.get("mer", "not_started") in _COMPLETED_STATES
    path_ready = pipeline_status.get("pathology", "not_started") in _COMPLETED_STATES

    if risk_status in _COMPLETED_STATES:
        # Risk completed, but check if inputs have newer versions
        risk_stale = await _is_risk_stale(case_id)
        if risk_stale and (mer_ready or path_ready):
            triggered.append("risk")
        else:
            skipped.append("risk (auto)")
    elif "mer" in triggered or "pathology" in triggered:
        skipped.append("risk (pending - auto-triggers after extraction)")
    elif _should_run(pipeline_status, "risk") and (mer_ready or path_ready):
        # Risk not started/failed but inputs ready → trigger
        triggered.append("risk")
    else:
        skipped.append("risk")

    if photo_files and id_files and _should_run(pipeline_status, "face_match"):
        triggered.append("face_match")
    else:
        skipped.append("face_match")

    # Location check is auto-triggered after pathology (needs lab OCR for address)
    location_status = pipeline_status.get("location_check", "not_started")
    if location_status in _COMPLETED_STATES:
        skipped.append("location_check (auto)")
    elif "pathology" in triggered and (photo_files or id_files):
        skipped.append("location_check (pending - auto-triggers after pathology)")
    else:
        skipped.append("location_check")

    return triggered, skipped


async def process_all_background(case_id: str, case: dict):
    """
    Background task: run all applicable pipelines in parallel.

    Called from BackgroundTasks after the API response is sent.
    Each pipeline updates its own pipeline_status in MongoDB.

    Auto-triggered pipelines:
    - Risk analysis: auto-triggers after MER/pathology extraction,
      OR runs directly when stale (input versions changed)
    - Location check: auto-triggers after pathology extraction (needs lab OCR)
    """
    pipeline_status = case.get("pipeline_status", {})
    mer_files = _get_uploaded_files(case, "mer")
    path_files = _get_uploaded_files(case, "pathology")
    photo_files = _get_uploaded_files(case, "photo")
    id_files = _get_uploaded_files(case, "id_proof")

    tasks = []
    run_risk_directly = False

    if mer_files and _should_run(pipeline_status, "mer"):
        tasks.append(_run_mer(case_id, mer_files))

    if path_files and _should_run(pipeline_status, "pathology"):
        tasks.append(_run_pathology(case_id, path_files))

    if photo_files and id_files and _should_run(pipeline_status, "face_match"):
        tasks.append(_run_face_match(case_id, photo_files, id_files))

    # Check if risk should run directly (stale or not_started with inputs ready)
    # Only when MER/pathology are NOT being triggered (they'd auto-trigger risk)
    mer_ready = pipeline_status.get("mer", "not_started") in _COMPLETED_STATES
    path_ready = pipeline_status.get("pathology", "not_started") in _COMPLETED_STATES
    mer_triggered = mer_files and _should_run(pipeline_status, "mer")
    path_triggered = path_files and _should_run(pipeline_status, "pathology")

    if not mer_triggered and not path_triggered and (mer_ready or path_ready):
        # MER/pathology won't run, check if risk needs to run
        risk_status = pipeline_status.get("risk", "not_started")
        if _should_run(pipeline_status, "risk"):
            # Risk is not_started or failed → run it
            run_risk_directly = True
        elif risk_status in _COMPLETED_STATES and await _is_risk_stale(case_id):
            # Risk completed but stale → re-run
            run_risk_directly = True

    if run_risk_directly:
        # Atomically set risk to processing to prevent duplicate runs
        db = await get_database()
        result = await db.cases.find_one_and_update(
            {
                "_id": ObjectId(case_id),
                "pipeline_status.risk": {"$nin": ["processing"]},
            },
            {
                "$set": {
                    "pipeline_status.risk": "processing",
                    "updated_at": datetime.utcnow(),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if result:
            logger.info(f"Running risk directly for case {case_id} (stale or ready)")
            tasks.append(_run_risk(case_id))

    # Note: location_check is auto-triggered after pathology completes
    # (via _maybe_trigger_location_check) since it needs lab OCR for address

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
