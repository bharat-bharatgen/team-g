from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class MatchDecision(str, Enum):
    MATCH = "match"
    NO_MATCH = "no_match"
    INCONCLUSIVE = "inconclusive"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class FaceMatchResultModel(BaseModel):
    case_id: str
    version: int = 1
    algorithm_version: str = "v1"  # "v1" (YuNet+SFace) or "v2" (InsightFace)

    # Input file references
    photo_file_id: str          # geo-tagged selfie
    id_file_id: str             # ID proof

    # Model output
    match: bool
    confidence: float           # raw cosine similarity (internal)
    match_percent: int          # user-friendly percentage (75%+ for match)
    person_face_count: int
    id_face_count: int
    decision: MatchDecision
    message: str

    # User review
    review_status: ReviewStatus = ReviewStatus.PENDING
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
