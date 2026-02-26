from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from app.core.security import get_current_user
from app.config import settings
from app.dependencies import get_database
from app.services.face_match.processor import (
    get_latest_result as get_latest_result_v1,
    update_review_status as update_review_status_v1,
)
from app.services.face_match_v2.processor import (
    get_latest_result as get_latest_result_v2,
    update_review_status as update_review_status_v2,
)
from app.services.storage import s3_service
from app.models.face_match_result import ReviewStatus
from app.api.v1.schemas.face_match import (
    FaceMatchResultResponse,
    FaceMatchReviewRequest,
    FaceMatchReviewResponse,
)

router = APIRouter()


def _get_latest_result_fn():
    """Get the appropriate get_latest_result function based on config."""
    if settings.face_match_algorithm == "v2":
        return get_latest_result_v2
    return get_latest_result_v1


def _get_update_review_fn():
    """Get the appropriate update_review_status function based on config."""
    if settings.face_match_algorithm == "v2":
        return update_review_status_v2
    return update_review_status_v1


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
    for doc_type, files in case.get("documents", {}).items():
        for f in files:
            if f.get("id") == file_id:
                return f.get("s3_key")
    return None


# ─── GET /cases/{case_id}/face-match ─────────────────────────────────────────

@router.get("/{case_id}/face-match", response_model=FaceMatchResultResponse)
async def get_face_match_result(case_id: str, user: dict = Depends(get_current_user)):
    """
    Get face-match result for a case.

    Returns the latest face-match result with presigned URLs for viewing
    both the geo-tagged photo and the ID proof image.
    """
    case = await _get_case_or_404(case_id, user["id"])

    get_latest_result = _get_latest_result_fn()
    doc = await get_latest_result(case_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No face-match result found. Run processing first.",
        )

    # Generate presigned URLs for the images
    photo_url = None
    id_url = None

    photo_s3_key = await _get_file_s3_key(case, doc["photo_file_id"])
    id_s3_key = await _get_file_s3_key(case, doc["id_file_id"])

    if photo_s3_key:
        photo_url = await s3_service.generate_download_url(photo_s3_key)
    if id_s3_key:
        id_url = await s3_service.generate_download_url(id_s3_key)

    return FaceMatchResultResponse(
        id=doc["_id"],
        case_id=doc["case_id"],
        version=doc["version"],
        algorithm_version=doc.get("algorithm_version", "v1"),
        match=doc["match"],
        match_percent=doc["match_percent"],
        decision=doc["decision"],
        message=doc["message"],
        photo_file_id=doc["photo_file_id"],
        id_file_id=doc["id_file_id"],
        photo_url=photo_url,
        id_url=id_url,
        review_status=doc["review_status"],
        reviewed_by=doc.get("reviewed_by"),
        reviewed_at=doc.get("reviewed_at"),
        review_comment=doc.get("review_comment"),
        created_at=doc["created_at"],
    )


# ─── PATCH /cases/{case_id}/face-match/review ────────────────────────────────

@router.patch("/{case_id}/face-match/review", response_model=FaceMatchReviewResponse)
async def review_face_match(
    case_id: str,
    body: FaceMatchReviewRequest,
    user: dict = Depends(get_current_user),
):
    """
    Approve or reject a face-match result.

    The user can approve or reject the system's face-match recommendation.
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

    update_review_status = _get_update_review_fn()
    updated = await update_review_status(
        case_id=case_id,
        review_status=review_status,
        reviewed_by=user["id"],
        comment=body.comment,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No face-match result found to review.",
        )

    # Update case pipeline status to "reviewed"
    db = await get_database()
    await db.cases.update_one(
        {"_id": ObjectId(case_id)},
        {"$set": {"pipeline_status.face_match": "reviewed"}},
    )

    return FaceMatchReviewResponse(
        case_id=case_id,
        review_status=updated["review_status"],
        reviewed_by=updated["reviewed_by"],
        reviewed_at=updated["reviewed_at"],
        review_comment=updated.get("review_comment"),
        message=f"Face-match result {review_status.value} successfully.",
    )
