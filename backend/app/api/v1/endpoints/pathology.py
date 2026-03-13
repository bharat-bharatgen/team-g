from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import StreamingResponse
from bson import ObjectId
import io

from app.core.security import get_current_user
from app.dependencies import get_database
from app.services.pathology.processor import (
    get_latest_result,
    get_result_by_version,
    list_result_versions,
)
from app.services.pathology.excel_export import generate_excel
from app.services.pathology.excel_import import import_excel
from app.models.pathology_result import PathologyResultModel, PathologyField
from app.api.v1.schemas.pathology import (
    PathologyResultResponse,
    PathologyFieldResponse,
    PathologyVersionsResponse,
    PathologyVersionEntry,
    PathologyImportResponse,
    PathologySummaryResponse,
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


# ─── GET /cases/{case_id}/pathology/result ───────────────────────────────────

@router.get("/{case_id}/pathology/result", response_model=PathologyResultResponse)
async def get_pathology_result(
    case_id: str,
    version: int = Query(None, description="Specific version number. Omit for latest."),
    user: dict = Depends(get_current_user),
):
    """
    Get pathology extraction result for a case.
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
            detail="No pathology result found. Run processing first.",
        )

    return PathologyResultResponse(
        id=doc["_id"],
        case_id=doc["case_id"],
        version=doc["version"],
        source=doc["source"],
        patient_info=doc.get("patient_info", {}),
        lab_info=doc.get("lab_info", {}),
        report_info=doc.get("report_info", {}),
        fields=[PathologyFieldResponse(**f) for f in doc["fields"]],
        created_at=doc["created_at"],
    )


# ─── GET /cases/{case_id}/pathology/summary ──────────────────────────────────

@router.get("/{case_id}/pathology/summary", response_model=PathologySummaryResponse)
async def get_pathology_summary(
    case_id: str,
    version: int = Query(None, description="Specific version. Omit for latest."),
    user: dict = Depends(get_current_user),
):
    """
    Get pathology summary statistics for a case.
    Returns counts of normal, abnormal, and no-range parameters.
    """
    await _get_case_or_404(case_id, user["id"])

    if version is not None:
        doc = await get_result_by_version(case_id, version)
    else:
        doc = await get_latest_result(case_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pathology result found. Run processing first.",
        )

    # Count fields by range_status
    fields = doc.get("fields", [])
    total = len(fields)
    normal_count = sum(1 for f in fields if f.get("range_status") == "normal")
    abnormal_count = sum(1 for f in fields if f.get("range_status") == "abnormal")
    no_range_count = total - normal_count - abnormal_count

    return PathologySummaryResponse(
        case_id=case_id,
        version=doc["version"],
        total=total,
        normal_count=normal_count,
        abnormal_count=abnormal_count,
        no_range_count=no_range_count,
    )


# ─── GET /cases/{case_id}/pathology/versions ─────────────────────────────────

@router.get("/{case_id}/pathology/versions", response_model=PathologyVersionsResponse)
async def get_pathology_versions(case_id: str, user: dict = Depends(get_current_user)):
    """List all pathology result versions for a case (metadata only)."""
    await _get_case_or_404(case_id, user["id"])

    versions = await list_result_versions(case_id)

    return PathologyVersionsResponse(
        case_id=case_id,
        versions=[
            PathologyVersionEntry(
                id=v["_id"],
                version=v["version"],
                source=v["source"],
                created_at=v["created_at"],
            )
            for v in versions
        ],
    )


# ─── GET /cases/{case_id}/pathology/export-excel ─────────────────────────────

@router.get("/{case_id}/pathology/export-excel")
async def export_pathology_excel(
    case_id: str,
    version: int = Query(None, description="Specific version. Omit for latest."),
    user: dict = Depends(get_current_user),
):
    """
    Download pathology result as an Excel (.xlsx) file.
    Dynamically generated — not stored. Green rows indicate user-edited fields.
    """
    await _get_case_or_404(case_id, user["id"])

    if version is not None:
        doc = await get_result_by_version(case_id, version)
    else:
        doc = await get_latest_result(case_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pathology result found. Run processing first.",
        )

    # Reconstruct PathologyField objects from stored dicts
    fields = [PathologyField(**f) for f in doc["fields"]]
    ver = doc["version"]

    excel_bytes = generate_excel(fields, case_id, ver)

    filename = f"Pathology_{case_id}_v{ver}.xlsx"

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ─── POST /cases/{case_id}/pathology/import-excel ────────────────────────────

@router.post("/{case_id}/pathology/import-excel", response_model=PathologyImportResponse)
async def import_pathology_excel(
    case_id: str,
    file: UploadFile = File(..., description="Edited .xlsx file"),
    user: dict = Depends(get_current_user),
):
    """
    Upload an edited Excel file to create a new versioned pathology result snapshot.

    Changed fields get source="user".
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
            detail="No pathology result found to compare against. Run processing first.",
        )

    # Reconstruct the previous PathologyResultModel
    prev_result = PathologyResultModel(
        case_id=prev_doc["case_id"],
        version=prev_doc["version"],
        source=prev_doc["source"],
        pages=prev_doc.get("pages", {}),
        patient_info=prev_doc.get("patient_info", {}),
        lab_info=prev_doc.get("lab_info", {}),
        report_info=prev_doc.get("report_info", {}),
        standardized=prev_doc.get("standardized", {}),
        fields=[PathologyField(**f) for f in prev_doc["fields"]],
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
    insert_result = await db.pathology_results.insert_one(insert_doc)
    doc_id = str(insert_result.inserted_id)

    # Update pathology pipeline status
    await db.cases.update_one(
        {"_id": ObjectId(case_id)},
        {"$set": {"pipeline_status.pathology": "reviewed"}},
    )

    # Re-trigger downstream pipelines (risk, test verification, location check)
    from app.services.orchestrator import trigger_downstream_after_edit
    await trigger_downstream_after_edit(case_id, "pathology")

    # Count changed fields
    changed = sum(1 for f in new_result.fields if f.source == "user")

    return PathologyImportResponse(
        id=doc_id,
        case_id=case_id,
        version=new_result.version,
        source="excel_import",
        fields_count=len(new_result.fields),
        changed_fields=changed,
        message=f"Created version {new_result.version} with {changed} field(s) changed.",
    )
