from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from app.core.security import get_current_user
from app.dependencies import get_database
from app.services.location_check.processor import get_latest_result, update_review_status
from app.services.storage import s3_service
from app.models.location_check_result import ReviewStatus
from app.api.v1.schemas.location_check import (
    LocationCheckResultResponse,
    LocationSourceResponse,
    DistanceResultResponse,
    LocationCheckReviewRequest,
    LocationCheckReviewResponse,
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


async def _get_file_s3_key(case: dict, file_id: str) -> str | None:
    """Find the S3 key for a file ID in a case's documents."""
    if not file_id:
        return None
    for doc_type, files in case.get("documents", {}).items():
        for f in files:
            if f.get("id") == file_id:
                return f.get("s3_key")
    return None


# ─── GET /cases/{case_id}/location-check ─────────────────────────────────────

@router.get("/{case_id}/location-check", response_model=LocationCheckResultResponse)
async def get_location_check_result(case_id: str, user: dict = Depends(get_current_user)):
    """
    Get location check result for a case.

    Returns the latest location check result showing:
    - Which sources were detected vs not detected
    - Extracted addresses/coordinates for each source
    - Pairwise distances between detected sources
    - Pass/fail decision based on distance threshold
    """
    case = await _get_case_or_404(case_id, user["id"])

    doc = await get_latest_result(case_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No location check result found. Run processing first.",
        )

    # Generate presigned URLs for the images
    photo_url = None
    id_url = None

    if doc.get("photo_file_id"):
        photo_s3_key = await _get_file_s3_key(case, doc["photo_file_id"])
        if photo_s3_key:
            photo_url = await s3_service.generate_download_url(photo_s3_key)

    if doc.get("id_file_id"):
        id_s3_key = await _get_file_s3_key(case, doc["id_file_id"])
        if id_s3_key:
            id_url = await s3_service.generate_download_url(id_s3_key)

    # Convert sources to response format
    sources = [
        LocationSourceResponse(
            source_type=s["source_type"],
            status=s["status"],
            raw_input=s.get("raw_input"),
            address=s.get("address"),
            coords=tuple(s["coords"]) if s.get("coords") else None,
            message=s.get("message"),
        )
        for s in doc.get("sources", [])
    ]

    # Convert distances to response format
    distances = [
        DistanceResultResponse(
            source_a=d["source_a"],
            source_b=d["source_b"],
            distance_km=d["distance_km"],
            flag=d["flag"],
        )
        for d in doc.get("distances", [])
    ]

    return LocationCheckResultResponse(
        id=doc["_id"],
        case_id=doc["case_id"],
        version=doc["version"],
        photo_file_id=doc.get("photo_file_id"),
        id_file_id=doc.get("id_file_id"),
        pathology_version=doc.get("pathology_version"),
        photo_url=photo_url,
        id_url=id_url,
        sources=sources,
        distances=distances,
        sources_detected=doc.get("sources_detected", []),
        sources_not_detected=doc.get("sources_not_detected", []),
        decision=doc["decision"],
        flags=doc.get("flags", []),
        message=doc["message"],
        review_status=doc["review_status"],
        reviewed_by=doc.get("reviewed_by"),
        reviewed_at=doc.get("reviewed_at"),
        review_comment=doc.get("review_comment"),
        created_at=doc["created_at"],
    )


# ─── PATCH /cases/{case_id}/location-check/review ────────────────────────────

@router.patch("/{case_id}/location-check/review", response_model=LocationCheckReviewResponse)
async def review_location_check(
    case_id: str,
    body: LocationCheckReviewRequest,
    user: dict = Depends(get_current_user),
):
    """
    Approve or reject a location check result.

    The user can approve or reject the system's location check recommendation.
    This is used for audit/compliance purposes.
    """
    await _get_case_or_404(case_id, user["id"])

    # Validate status
    try:
        review_status = ReviewStatus(body.status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {[s.value for s in ReviewStatus if s != ReviewStatus.PENDING]}",
        )

    if review_status == ReviewStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot set status to 'pending'. Use 'approved' or 'rejected'.",
        )

    updated = await update_review_status(
        case_id=case_id,
        review_status=review_status,
        reviewed_by=user["id"],
        comment=body.comment,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No location check result found to review.",
        )

    # Update case pipeline status to "reviewed"
    db = await get_database()
    await db.cases.update_one(
        {"_id": ObjectId(case_id)},
        {"$set": {"pipeline_status.location_check": "reviewed"}},
    )

    return LocationCheckReviewResponse(
        case_id=case_id,
        review_status=updated["review_status"],
        reviewed_by=updated["reviewed_by"],
        reviewed_at=updated["reviewed_at"],
        review_comment=updated.get("review_comment"),
        message=f"Location check result {review_status.value} successfully.",
    )
