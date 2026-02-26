from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ─── Process response ────────────────────────────────────────────────────────

class ClassificationSummary(BaseModel):
    mapping_summary: Dict[str, Any] = {}
    unmatched_pages: List[dict] = []
    missing_pages: List[int] = []
    needs_review: List[dict] = []


class TestVerificationSummary(BaseModel):
    """Summary of test verification (if Page 5 was detected)."""
    status: str  # "complete" | "missing_tests" | "requirements_page_not_found"
    total_required: int = 0
    total_found: int = 0
    total_missing: int = 0
    missing_tests: List[str] = []


class MERProcessResponse(BaseModel):
    id: str
    case_id: str
    version: int
    source: str
    fields_count: int
    classification: ClassificationSummary
    test_verification: Optional[TestVerificationSummary] = None


# ─── Result response ─────────────────────────────────────────────────────────

class MERFieldResponse(BaseModel):
    id: str
    page: int
    section: str
    key: str
    value: Optional[str] = None
    answer: Optional[str] = None
    details: Optional[str] = None
    confidence: Optional[float] = None
    source: str


class MERResultResponse(BaseModel):
    id: str
    case_id: str
    version: int
    source: str
    classification: Dict[str, Any]
    pages: Dict[str, Any]
    fields: List[MERFieldResponse]
    created_at: datetime


# ─── Version list ─────────────────────────────────────────────────────────────

class MERVersionEntry(BaseModel):
    id: str
    version: int
    source: str
    created_at: datetime


class MERVersionsResponse(BaseModel):
    case_id: str
    versions: List[MERVersionEntry]


# ─── Excel import response ───────────────────────────────────────────────────

class MERImportResponse(BaseModel):
    id: str
    case_id: str
    version: int
    source: str
    fields_count: int
    changed_fields: int
    message: str


# ─── Patient info response ───────────────────────────────────────────────────

class PatientInfoResponse(BaseModel):
    available: bool
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    dob: Optional[str] = None
    proposal_number: Optional[str] = None


# ─── Summary response ────────────────────────────────────────────────────────

class MERSummaryResponse(BaseModel):
    case_id: str
    version: int
    total_fields: int
    high_confidence_count: int  # >= 90%
    low_confidence_count: int   # < 90%
    yes_answer_count: int       # Y/N questions with "Yes" (flags/deviations)
