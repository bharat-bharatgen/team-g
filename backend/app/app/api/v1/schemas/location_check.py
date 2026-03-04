from datetime import datetime
from typing import List, Optional, Tuple
from pydantic import BaseModel


class LocationSourceResponse(BaseModel):
    """Single location source extraction result."""
    source_type: str               # "photo" | "id_card" | "lab"
    status: str                    # "found" | "not_found" | "skipped" | "geocode_failed"
    raw_input: Optional[str] = None
    address: Optional[str] = None
    coords: Optional[Tuple[float, float]] = None
    message: Optional[str] = None


class DistanceResultResponse(BaseModel):
    """Pairwise distance between two sources."""
    source_a: str
    source_b: str
    distance_km: float
    flag: bool


class LocationCheckResultResponse(BaseModel):
    id: str
    case_id: str
    version: int

    # Input references
    photo_file_id: Optional[str] = None
    id_file_id: Optional[str] = None
    pathology_version: Optional[int] = None

    # Presigned URLs for images
    photo_url: Optional[str] = None
    id_url: Optional[str] = None

    # Extraction results
    sources: List[LocationSourceResponse]
    distances: List[DistanceResultResponse]

    # Summary
    sources_detected: List[str]
    sources_not_detected: List[str]

    # Decision
    decision: str                  # "pass" | "needs_review" | "fail" | "insufficient"
    flags: List[str]
    message: str

    # Review
    review_status: str             # "pending" | "approved" | "rejected"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None

    created_at: datetime


class LocationCheckReviewRequest(BaseModel):
    status: str  # "approved" | "rejected"
    comment: Optional[str] = None


class LocationCheckReviewResponse(BaseModel):
    case_id: str
    review_status: str
    reviewed_by: str
    reviewed_at: datetime
    review_comment: Optional[str] = None
    message: str
