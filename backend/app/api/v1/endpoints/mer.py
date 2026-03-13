from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import StreamingResponse
from bson import ObjectId
import io

from app.core.security import get_current_user
from app.dependencies import get_database
from app.services.mer.processor import (
    get_latest_result,
    get_result_by_version,
    list_result_versions,
)
from app.services.task_queue import enqueue_task
from app.services.mer.excel_export import generate_excel
from app.services.mer.excel_import import import_excel
from app.models.mer_result import MERResultModel, MERField
from app.api.v1.schemas.mer import (
    MERResultResponse,
    MERFieldResponse,
    MERVersionsResponse,
    MERVersionEntry,
    MERImportResponse,
    PatientInfoResponse,
    MERSummaryResponse,
)

router = APIRouter()


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _get_case_or_404(case_id: str, user_id: str):
    """Fetch a case and verify ownership."""
    db = await get_database()
    case = await db.cases.find_one({"_id": ObjectId(case_id), "user_id": user_id})
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


def _get_mer_files(case: dict) -> list[dict]:
    """Extract uploaded MER file entries from a case document."""
    mer_files = case.get("documents", {}).get("mer", [])
    uploaded = [f for f in mer_files if f.get("status") == "uploaded"]
    if not uploaded:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No uploaded MER documents found. Upload MER files first.",
        )
    return uploaded


# ─── POST /cases/{case_id}/mer/process ───────────────────────────────────────

@router.post("/{case_id}/mer/process")
async def trigger_mer_processing(case_id: str, user: dict = Depends(get_current_user)):
    """
    Queue MER processing for background execution.

    Returns immediately. Poll GET /cases/{id}/status for progress.
    """
    case = await _get_case_or_404(case_id, user["id"])

    mer_status = case.get("pipeline_status", {}).get("mer", "not_started")
    if mer_status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="MER processing is already in progress.",
        )

    _get_mer_files(case)

    db = await get_database()
    await db.cases.update_one(
        {"_id": ObjectId(case_id)},
        {"$set": {"pipeline_status.mer": "processing"}},
    )
    await enqueue_task(case_id, "mer")

    return {"case_id": case_id, "status": "processing", "message": "MER processing queued."}


# ─── GET /cases/{case_id}/mer/result ─────────────────────────────────────────

@router.get("/{case_id}/mer/result", response_model=MERResultResponse)
async def get_mer_result(
    case_id: str,
    version: int = Query(None, description="Specific version number. Omit for latest."),
    user: dict = Depends(get_current_user),
):
    """
    Get MER extraction result for a case.
    Returns latest version by default, or a specific version if ?version=N is provided.
    """
    await _get_case_or_404(case_id, user["id"])

    if version is not None:
        doc = await get_result_by_version(case_id, version)
    else:
        doc = await get_latest_result(case_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No MER result found. Run processing first.",
        )

    return MERResultResponse(
        id=doc["_id"],
        case_id=doc["case_id"],
        version=doc["version"],
        source=doc["source"],
        classification=doc["classification"],
        pages=doc["pages"],
        fields=[MERFieldResponse(**f) for f in doc["fields"]],
        created_at=doc["created_at"],
    )


# ─── GET /cases/{case_id}/mer/versions ───────────────────────────────────────

@router.get("/{case_id}/mer/versions", response_model=MERVersionsResponse)
async def get_mer_versions(case_id: str, user: dict = Depends(get_current_user)):
    """List all MER result versions for a case (metadata only)."""
    await _get_case_or_404(case_id, user["id"])

    versions = await list_result_versions(case_id)

    return MERVersionsResponse(
        case_id=case_id,
        versions=[
            MERVersionEntry(
                id=v["_id"],
                version=v["version"],
                source=v["source"],
                created_at=v["created_at"],
            )
            for v in versions
        ],
    )


# ─── GET /cases/{case_id}/mer/export-excel ───────────────────────────────────

@router.get("/{case_id}/mer/export-excel")
async def export_mer_excel(
    case_id: str,
    version: int = Query(None, description="Specific version. Omit for latest."),
    user: dict = Depends(get_current_user),
):
    """
    Download MER result as an Excel (.xlsx) file.
    Dynamically generated — not stored. Colors indicate confidence levels.
    """
    await _get_case_or_404(case_id, user["id"])

    if version is not None:
        doc = await get_result_by_version(case_id, version)
    else:
        doc = await get_latest_result(case_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No MER result found. Run processing first.",
        )

    # Reconstruct MERField objects from stored dicts
    fields = [MERField(**f) for f in doc["fields"]]
    ver = doc["version"]

    excel_bytes = generate_excel(fields, case_id, ver)

    filename = f"MER_{case_id}_v{ver}.xlsx"

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ─── POST /cases/{case_id}/mer/import-excel ──────────────────────────────────

@router.post("/{case_id}/mer/import-excel", response_model=MERImportResponse)
async def import_mer_excel(
    case_id: str,
    file: UploadFile = File(..., description="Edited .xlsx file"),
    user: dict = Depends(get_current_user),
):
    """
    Upload an edited Excel file to create a new versioned MER result snapshot.

    Changed fields get source="user" and confidence=1.0.
    Unchanged fields keep their original values.
    """
    await _get_case_or_404(case_id, user["id"])

    # Validate file type
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .xlsx files are accepted.",
        )

    # Get the latest result as the base for comparison
    prev_doc = await get_latest_result(case_id)
    if not prev_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No MER result found to compare against. Run processing first.",
        )

    # Reconstruct the previous MERResultModel
    prev_result = MERResultModel(
        case_id=prev_doc["case_id"],
        version=prev_doc["version"],
        source=prev_doc["source"],
        classification=prev_doc["classification"],
        pages=prev_doc["pages"],
        fields=[MERField(**f) for f in prev_doc["fields"]],
        created_at=prev_doc["created_at"],
    )

    # Read uploaded file
    file_bytes = await file.read()

    try:
        new_result = import_excel(file_bytes, prev_result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process Excel: {str(e)}",
        )

    # Store the new version
    db = await get_database()
    insert_doc = new_result.model_dump()
    insert_result = await db.mer_results.insert_one(insert_doc)
    doc_id = str(insert_result.inserted_id)

    # Update MER pipeline status
    await db.cases.update_one(
        {"_id": ObjectId(case_id)},
        {"$set": {"pipeline_status.mer": "reviewed"}},
    )

    # Re-trigger downstream pipelines (risk, test verification)
    from app.services.orchestrator import trigger_downstream_after_edit
    await trigger_downstream_after_edit(case_id, "mer")

    # Count changed fields
    changed = sum(1 for f in new_result.fields if f.source == "user")

    return MERImportResponse(
        id=doc_id,
        case_id=case_id,
        version=new_result.version,
        source="excel_import",
        fields_count=len(new_result.fields),
        changed_fields=changed,
        message=f"Created version {new_result.version} with {changed} field(s) changed.",
    )


# ─── GET /cases/{case_id}/mer/patient-info ────────────────────────────────────

def _parse_numeric(value: str) -> int | None:
    """Parse a numeric string, returning None if invalid."""
    if not value:
        return None
    cleaned = ''.join(c for c in str(value) if c.isdigit() or c == '.')
    if cleaned:
        try:
            return int(float(cleaned))
        except ValueError:
            return None
    return None


@router.get("/{case_id}/mer/patient-info", response_model=PatientInfoResponse)
async def get_patient_info(case_id: str, user: dict = Depends(get_current_user)):
    """
    Get patient information extracted from MER.
    Returns basic demographics: name, age, gender, DOB, proposal number.
    """
    await _get_case_or_404(case_id, user["id"])

    doc = await get_latest_result(case_id)

    if not doc:
        return PatientInfoResponse(available=False)

    # Extract patient info from page 1 header
    # Pages are stored with keys "1", "2", etc.
    pages = doc.get("pages", {})
    page1 = pages.get("1", {})
    header = page1.get("header", {})

    name = header.get("Full Name of Life Assured", {}).get("value")
    age = _parse_numeric(header.get("Age", {}).get("value"))
    gender = header.get("Gender", {}).get("value")
    dob = header.get("Date of Birth", {}).get("value")
    proposal_number = header.get("Proposal Number / Policy Number", {}).get("value")

    return PatientInfoResponse(
        available=True,
        name=name,
        age=age,
        gender=gender,
        dob=dob,
        proposal_number=proposal_number,
    )


# ─── GET /cases/{case_id}/mer/summary ─────────────────────────────────────────

@router.get("/{case_id}/mer/summary", response_model=MERSummaryResponse)
async def get_mer_summary(
    case_id: str,
    version: int = Query(None, description="Specific version. Omit for latest."),
    user: dict = Depends(get_current_user),
):
    """
    Get MER summary statistics for a case.
    Returns counts of fields by confidence level and Yes answers (flags).
    """
    await _get_case_or_404(case_id, user["id"])

    if version is not None:
        doc = await get_result_by_version(case_id, version)
    else:
        doc = await get_latest_result(case_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No MER result found. Run processing first.",
        )

    fields = doc.get("fields", [])
    total_fields = len(fields)
    
    # Count by confidence threshold (90%). Null confidence = no value → count as high (not <90%)
    high_confidence_count = sum(
        1 for f in fields
        if f.get("confidence") is None or (f.get("confidence") is not None and f["confidence"] >= 0.9)
    )
    low_confidence_count = total_fields - high_confidence_count
    
    # Questions where "Yes" is the IDEAL answer (not a flag)
    # These are positive questions where "No" would be concerning
    positive_questions = {
        "5) Does applicant appear medically fit?",
        "7) Is your vision and hearing normal?",
    }
    
    # Count flags (deviations from ideal):
    # - "Yes" on negative questions (indicates medical conditions)
    # - "No" on positive questions (not fit, not normal)
    yes_flags = sum(
        1 for f in fields 
        if (f.get("answer") or "").lower() == "yes"
        and f.get("key", "") not in positive_questions
    )
    
    no_flags = sum(
        1 for f in fields 
        if (f.get("answer") or "").lower() == "no"
        and f.get("key", "") in positive_questions
    )
    
    yes_answer_count = yes_flags + no_flags

    return MERSummaryResponse(
        case_id=case_id,
        version=doc["version"],
        total_fields=total_fields,
        high_confidence_count=high_confidence_count,
        low_confidence_count=low_confidence_count,
        yes_answer_count=yes_answer_count,
    )
