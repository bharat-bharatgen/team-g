from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class LocationDecision(str, Enum):
    PASS = "pass"                  # all distances <= 15 km
    NEEDS_REVIEW = "needs_review"  # any distance 15-30 km (none > 30)
    FAIL = "fail"                  # any distance > 30 km
    INSUFFICIENT = "insufficient"  # < 2 sources with valid coords


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SourceStatus(str, Enum):
    FOUND = "found"                # address/coords extracted successfully
    NOT_FOUND = "not_found"        # document present but no address found
    SKIPPED = "skipped"            # document not uploaded
    GEOCODE_FAILED = "geocode_failed"  # address found but geocoding failed


class LocationSource(BaseModel):
    """Single location source extraction result."""
    source_type: str               # "photo" | "id_card" | "lab"
    status: SourceStatus
    raw_input: Optional[str] = None   # address text or "lat,lon" from LLM
    address: Optional[str] = None     # human-readable address
    coords: Optional[Tuple[float, float]] = None  # (lat, lon)
    message: Optional[str] = None     # explanation if not found


class DistanceResult(BaseModel):
    """Pairwise distance between two sources."""
    source_a: str                  # "photo" | "id_card" | "lab"
    source_b: str
    distance_km: float
    flag: bool = False             # True if distance > threshold


class LocationCheckResultModel(BaseModel):
    case_id: str
    version: int = 1

    # Input file references (null if not uploaded)
    photo_file_id: Optional[str] = None
    id_file_id: Optional[str] = None
    pathology_version: Optional[int] = None  # version used for lab address

    # Extraction results - shows status for ALL sources
    sources: List[LocationSource] = Field(default_factory=list)

    # Distance comparisons (only for sources with valid coords)
    distances: List[DistanceResult] = Field(default_factory=list)

    # Summary
    sources_detected: List[str] = Field(default_factory=list)   # ["photo", "lab"]
    sources_not_detected: List[str] = Field(default_factory=list)  # ["id_card"]

    # Decision
    decision: LocationDecision
    flags: List[str] = Field(default_factory=list)
    message: str

    # User review
    review_status: ReviewStatus = ReviewStatus.PENDING
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
