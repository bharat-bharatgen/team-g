from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class FaceMatchResultResponse(BaseModel):
    id: str
    case_id: str
    version: int
    algorithm_version: str = "v1"  # "v1" (YuNet+SFace) or "v2" (InsightFace)
    match: bool
    match_percent: int            # user-friendly percentage (75%+ for match)
    decision: str                 # "match" | "no_match" | "inconclusive"
    message: str
    photo_file_id: str
    id_file_id: str
    photo_url: Optional[str] = None   # presigned URL for display
    id_url: Optional[str] = None      # presigned URL for display
    review_status: str            # "pending" | "approved" | "rejected"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None
    created_at: datetime


class FaceMatchReviewRequest(BaseModel):
    status: str  # "approved" | "rejected"
    comment: Optional[str] = None


class FaceMatchReviewResponse(BaseModel):
    case_id: str
    review_status: str
    reviewed_by: str
    reviewed_at: datetime
    review_comment: Optional[str] = None
    message: str
