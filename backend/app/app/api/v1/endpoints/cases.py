import asyncio
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from bson import ObjectId
from app.api.v1.schemas.case import (
    CaseCreate,
    CaseResponse,
    CaseListResponse,
    ProcessAllResponse,
    CaseStatusResponse,
    PipelineStatusDetail,
    DecisionRequest,
    DecisionResponse,
    CaseDashboardSummary,
    CaseDashboardResponse,
    CaseDeleteResponse,
)
from app.models.case import CaseModel, CaseDecision
from app.core.security import get_current_user
from app.dependencies import get_database
from app.services.orchestrator import get_pipelines_to_trigger
from app.services.task_queue import enqueue_task

router = APIRouter()


# ─── Status helpers ──────────────────────────────────────────────────────────

async def _get_result_metadata(db, collection: str, case_id: str) -> dict:
    """Get latest result metadata (version, fields_count, source, created_at) from a collection."""
    result = await db[collection].find_one(
        {"case_id": case_id},
        sort=[("version", -1)],
        projection={"version": 1, "fields": 1, "source": 1, "created_at": 1},
    )
    if result:
        fields = result.get("fields", [])
        return {
            "version": result.get("version"),
            "fields_count": len(fields) if isinstance(fields, list) else None,
            "source": result.get("source"),
            "created_at": result.get("created_at"),
        }
    return {}


async def _get_face_match_metadata(db, case_id: str) -> dict:
    """Get face-match specific metadata for dashboard display."""
    result = await db.face_match_results.find_one(
        {"case_id": case_id},
        sort=[("version", -1)],
        projection={
            "version": 1,
            "created_at": 1,
            "match_percent": 1,
            "match": 1,
            "decision": 1,
            "review_status": 1,
        },
    )
    if result:
        return {
            "version": result.get("version"),
            "created_at": result.get("created_at"),
            "match_percent": result.get("match_percent"),
            "match": result.get("match"),
            "recommendation": result.get("decision"),
            "review_status": result.get("review_status"),
        }
    return {}


def _case_to_response(case: dict) -> CaseResponse:
    return CaseResponse(
        id=str(case["_id"]),
        case_name=case.get("case_name"),
        pipeline_status=case.get("pipeline_status", {}),
        pipeline_errors=case.get("pipeline_errors", {}),
        documents=case.get("documents", {}),
        decision=case.get("decision"),
        decision_by=case.get("decision_by"),
        decision_at=case.get("decision_at"),
        decision_comment=case.get("decision_comment"),
        created_at=case["created_at"],
        updated_at=case["updated_at"],
    )


@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(request: CaseCreate, user: dict = Depends(get_current_user)):
    db = await get_database()
    case = CaseModel(user_id=user["id"], case_name=request.case_name)
    result = await db.cases.insert_one(case.model_dump())
    created = await db.cases.find_one({"_id": result.inserted_id})
    return _case_to_response(created)


@router.get("/", response_model=CaseListResponse)
async def list_cases(user: dict = Depends(get_current_user)):
    db = await get_database()
    cursor = db.cases.find({"user_id": user["id"], "is_deleted": {"$ne": True}}).sort("created_at", -1)
    cases = await cursor.to_list(length=100)
    return CaseListResponse(cases=[_case_to_response(c) for c in cases])


# ─── Dashboard endpoint (optimized with batch fetching) ───────────────────────

# MER sections that typically have low confidence (text, comments, signatures)
_LOW_CONFIDENCE_EXEMPT_SECTIONS = {
    "signature",
    "declaration",
    "comments",
    "remarks",
    "notes",
}


def _build_latest_lookup(docs: List[dict], key: str = "case_id") -> Dict[str, dict]:
    """
    Build a lookup dict from a list of documents, keeping only the latest version per case_id.
    Documents should already be sorted by version descending from MongoDB.
    """
    lookup = {}
    for doc in docs:
        case_id = doc.get(key)
        if case_id and case_id not in lookup:
            # First occurrence is the latest (due to sort)
            lookup[case_id] = doc
    return lookup


def _compute_mer_stats(mer_doc: dict) -> tuple:
    """Compute MER confidence stats from a MER result document."""
    if not mer_doc:
        return None, None

    fields = mer_doc.get("fields", [])
    total = len(fields)
    if total == 0:
        return None, None

    # Null confidence = no value → do not count as low (treat as high)
    low_conf_count = sum(
        1
        for f in fields
        if f.get("confidence") is not None
        and f.get("confidence") < 0.9
        and f.get("section", "").lower() not in _LOW_CONFIDENCE_EXEMPT_SECTIONS
    )
    high_conf_count = total - low_conf_count
    pct = round((high_conf_count / total) * 100, 1)
    return pct, low_conf_count


def _build_case_summary(
    case: dict,
    risk_lookup: Dict[str, dict],
    tv_lookup: Dict[str, dict],
    mer_lookup: Dict[str, dict],
    fm_lookup: Dict[str, dict],
    lc_lookup: Dict[str, dict],
) -> CaseDashboardSummary:
    """Build a dashboard summary for a case using pre-fetched lookup dicts."""
    case_id = str(case["_id"])
    pipeline_status = case.get("pipeline_status", {})

    # Extract data from lookups
    risk_doc = risk_lookup.get(case_id)
    risk_level = risk_doc.get("llm_response", {}).get("risk_level") if risk_doc else None

    tv_doc = tv_lookup.get(case_id)
    tests_required = tv_doc.get("total_required") if tv_doc else None
    tests_found = tv_doc.get("total_found") if tv_doc else None

    mer_doc = mer_lookup.get(case_id)
    mer_high_confidence_pct, mer_low_confidence_count = _compute_mer_stats(mer_doc)

    fm_doc = fm_lookup.get(case_id)
    face_match_decision = fm_doc.get("decision") if fm_doc else None

    lc_doc = lc_lookup.get(case_id)
    location_check_decision = lc_doc.get("decision") if lc_doc else None

    # Compute needs_attention flag
    needs_attention = (
        (tests_required is not None and tests_found is not None and tests_found < tests_required)
        or (mer_low_confidence_count is not None and mer_low_confidence_count > 4)
        or face_match_decision == "no_match"
        or location_check_decision in ("fail", "needs_review")
        or risk_level == "High"
    )

    return CaseDashboardSummary(
        id=case_id,
        case_name=case.get("case_name"),
        created_at=case["created_at"],
        pipeline_status=pipeline_status,
        decision=case.get("decision"),
        risk_level=risk_level,
        tests_required=tests_required,
        tests_found=tests_found,
        mer_high_confidence_pct=mer_high_confidence_pct,
        mer_low_confidence_count=mer_low_confidence_count,
        face_match_decision=face_match_decision,
        location_check_decision=location_check_decision,
        needs_attention=needs_attention,
    )


class DashboardFilter(str, Enum):
    ALL = "all"
    PENDING = "pending"
    DECIDED = "decided"
    ATTENTION = "attention"


@router.get("/dashboard", response_model=CaseDashboardResponse)
async def get_dashboard(
    filter: DashboardFilter = Query(DashboardFilter.ALL, description="Filter cases"),
    user: dict = Depends(get_current_user),
):
    """
    Get enriched case list for dashboard display.

    Optimized with batch fetching - only 6 DB queries total instead of 5*N.

    Query params:
    - filter: all | pending | decided | attention

    Returns all cases with summary data including:
    - Risk level
    - Test verification status (X/Y found)
    - MER confidence percentage
    - Face match decision
    - Location check decision
    - Needs attention flag

    Also returns aggregate stats for the stats overview cards (computed on full dataset).
    """
    db = await get_database()

    # 1. Fetch all cases for user (excluding soft-deleted)
    cases = await db.cases.find({"user_id": user["id"], "is_deleted": {"$ne": True}}).sort("created_at", -1).to_list(100)

    if not cases:
        return CaseDashboardResponse(
            cases=[],
            total=0,
            awaiting_decision=0,
            decided=0,
            needs_attention_count=0,
            high_risk_count=0,
        )

    # 2. Get all case IDs
    case_ids = [str(c["_id"]) for c in cases]

    # 3. Batch fetch all results in parallel (5 queries instead of 5*N)
    risk_docs, tv_docs, mer_docs, fm_docs, lc_docs = await asyncio.gather(
        db.risk_results.find(
            {"case_id": {"$in": case_ids}},
            projection={"case_id": 1, "version": 1, "llm_response.risk_level": 1},
        ).sort("version", -1).to_list(None),
        db.test_verification_results.find(
            {"case_id": {"$in": case_ids}},
            projection={"case_id": 1, "version": 1, "total_required": 1, "total_found": 1},
        ).sort("version", -1).to_list(None),
        db.mer_results.find(
            {"case_id": {"$in": case_ids}},
            projection={"case_id": 1, "version": 1, "fields": 1},
        ).sort("version", -1).to_list(None),
        db.face_match_results.find(
            {"case_id": {"$in": case_ids}},
            projection={"case_id": 1, "version": 1, "decision": 1},
        ).sort("version", -1).to_list(None),
        db.location_check_results.find(
            {"case_id": {"$in": case_ids}},
            projection={"case_id": 1, "version": 1, "decision": 1},
        ).sort("version", -1).to_list(None),
    )

    # 4. Build lookup dicts (latest version per case_id)
    risk_lookup = _build_latest_lookup(risk_docs)
    tv_lookup = _build_latest_lookup(tv_docs)
    mer_lookup = _build_latest_lookup(mer_docs)
    fm_lookup = _build_latest_lookup(fm_docs)
    lc_lookup = _build_latest_lookup(lc_docs)

    # 5. Build summaries (no DB calls, just dict lookups)
    all_summaries = [
        _build_case_summary(case, risk_lookup, tv_lookup, mer_lookup, fm_lookup, lc_lookup)
        for case in cases
    ]

    # 6. Compute aggregate stats (on full dataset, before filtering)
    total = len(all_summaries)
    awaiting_decision = sum(1 for s in all_summaries if s.decision is None)
    decided = total - awaiting_decision
    needs_attention_count = sum(1 for s in all_summaries if s.needs_attention)
    high_risk_count = sum(1 for s in all_summaries if s.risk_level == "High")

    # 7. Apply filter
    if filter == DashboardFilter.PENDING:
        filtered_summaries = [s for s in all_summaries if s.decision is None]
    elif filter == DashboardFilter.DECIDED:
        filtered_summaries = [s for s in all_summaries if s.decision is not None]
    elif filter == DashboardFilter.ATTENTION:
        filtered_summaries = [s for s in all_summaries if s.needs_attention]
    else:
        filtered_summaries = all_summaries

    return CaseDashboardResponse(
        cases=filtered_summaries,
        total=total,
        awaiting_decision=awaiting_decision,
        decided=decided,
        needs_attention_count=needs_attention_count,
        high_risk_count=high_risk_count,
    )


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(case_id: str, user: dict = Depends(get_current_user)):
    db = await get_database()
    case = await db.cases.find_one({"_id": ObjectId(case_id), "user_id": user["id"]})
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return _case_to_response(case)


@router.get("/{case_id}/status", response_model=CaseStatusResponse)
async def get_case_status(case_id: str, user: dict = Depends(get_current_user)):
    """
    Lightweight polling endpoint for pipeline statuses.

    Designed for frontend polling at 2-3 second intervals while pipelines are running.
    Returns only pipeline_status with enriched metadata — no documents payload.

    For pipelines that have produced results (extracted/reviewed), the response
    includes version, fields_count, source, and created_at from the result collection.
    """
    db = await get_database()
    case = await db.cases.find_one({"_id": ObjectId(case_id), "user_id": user["id"]})
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    pipeline_status = case.get("pipeline_status", {})
    pipeline_errors = case.get("pipeline_errors", {})

    # Map pipeline names to their result collections
    pipeline_collections = {
        "mer": "mer_results",
        "pathology": "pathology_results",
        "risk": "risk_results",
        "test_verification": "test_verification_results",
    }

    enriched_status = {}
    for pipeline, current_status in pipeline_status.items():
        detail = PipelineStatusDetail(status=current_status)

        # Enrich with error when failed
        if current_status == "failed":
            err = pipeline_errors.get(pipeline) or {}
            detail = PipelineStatusDetail(
                status=current_status,
                error_message=err.get("message"),
                error_traceback=err.get("traceback"),
            )
        # Enrich with result metadata if pipeline has results
        elif current_status in ("extracted", "reviewed"):
            if pipeline == "face_match":
                # Face-match has different metadata structure
                metadata = await _get_face_match_metadata(db, case_id)
                detail = PipelineStatusDetail(status=current_status, **metadata)
            elif pipeline in pipeline_collections:
                metadata = await _get_result_metadata(db, pipeline_collections[pipeline], case_id)
                detail = PipelineStatusDetail(status=current_status, **metadata)

        enriched_status[pipeline] = detail

    return CaseStatusResponse(
        case_id=case_id,
        case_name=case.get("case_name"),
        pipeline_status=enriched_status,
        pipeline_errors=pipeline_errors,
        decision=case.get("decision"),
        decision_by=case.get("decision_by"),
        decision_at=case.get("decision_at"),
        updated_at=case["updated_at"],
    )


@router.post("/{case_id}/process-all", response_model=ProcessAllResponse)
async def trigger_process_all(
    case_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Trigger all applicable processing pipelines for a case.

    Returns immediately with what pipelines will be triggered.
    A background worker picks up and processes each task.
    Poll GET /cases/{id}/status for progress.
    """
    db = await get_database()
    case = await db.cases.find_one({"_id": ObjectId(case_id), "user_id": user["id"]})
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    triggered, skipped = await get_pipelines_to_trigger(case_id, case)

    if triggered:
        now = datetime.utcnow()
        status_updates = {
            f"pipeline_status.{p}": "processing" for p in triggered
        }
        status_updates["updated_at"] = now
        await db.cases.update_one(
            {"_id": ObjectId(case_id)}, {"$set": status_updates}
        )
        for pipeline in triggered:
            await enqueue_task(case_id, pipeline)

    return ProcessAllResponse(
        case_id=case_id,
        pipelines_triggered=triggered,
        pipelines_skipped=skipped,
        results={},
    )


# ─── Decision endpoint ────────────────────────────────────────────────────────


@router.patch("/{case_id}/decision", response_model=DecisionResponse)
async def set_case_decision(
    case_id: str,
    request: DecisionRequest,
    user: dict = Depends(get_current_user),
):
    """
    Set the underwriter decision for a case.

    Decision values:
    - approved: Application accepted
    - review: Needs further investigation / senior review
    - declined: Application rejected
    """
    db = await get_database()
    case = await db.cases.find_one({"_id": ObjectId(case_id), "user_id": user["id"]})
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    # Validate decision value
    valid_decisions = [d.value for d in CaseDecision]
    if request.decision not in valid_decisions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision. Must be one of: {', '.join(valid_decisions)}",
        )

    now = datetime.utcnow()
    await db.cases.update_one(
        {"_id": ObjectId(case_id)},
        {
            "$set": {
                "decision": request.decision,
                "decision_by": user["id"],
                "decision_at": now,
                "decision_comment": request.comment,
                "updated_at": now,
            }
        },
    )

    return DecisionResponse(
        case_id=case_id,
        decision=request.decision,
        decision_by=user["id"],
        decision_at=now,
        decision_comment=request.comment,
        message=f"Case decision set to '{request.decision}' successfully.",
    )


# ─── Delete case (soft delete) ─────────────────────────────────────────────────


@router.delete("/{case_id}", response_model=CaseDeleteResponse)
async def delete_case(case_id: str, user: dict = Depends(get_current_user)):
    """
    Soft-delete a case by setting is_deleted flag.

    The case will no longer appear in list or dashboard views.
    """
    db = await get_database()
    case = await db.cases.find_one({"_id": ObjectId(case_id), "user_id": user["id"]})
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    await db.cases.update_one(
        {"_id": ObjectId(case_id)},
        {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}},
    )

    return CaseDeleteResponse(case_id=case_id, message="Case deleted successfully.")

