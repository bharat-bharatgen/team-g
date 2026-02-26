from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class CaseCreate(BaseModel):
    case_name: Optional[str] = None


# ─── Status response (lightweight polling) ───────────────────────────────────

class PipelineStatusDetail(BaseModel):
    """Enriched pipeline status with result metadata."""
    status: str
    version: Optional[int] = None
    fields_count: Optional[int] = None
    source: Optional[str] = None
    created_at: Optional[datetime] = None

    # Error info when status is "failed"
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None

    # Face-match specific fields (only populated for face_match pipeline)
    match_percent: Optional[int] = None       # user-friendly percentage (75%+ for match)
    match: Optional[bool] = None              # True/False
    recommendation: Optional[str] = None      # "match" | "no_match" | "inconclusive"
    review_status: Optional[str] = None       # "pending" | "approved" | "rejected"


class CaseStatusResponse(BaseModel):
    """Lightweight status response for polling."""
    case_id: str
    case_name: Optional[str] = None
    pipeline_status: Dict[str, PipelineStatusDetail]
    pipeline_errors: Dict[str, dict] = {}
    # Human decision
    decision: Optional[str] = None  # approved | review | declined
    decision_by: Optional[str] = None
    decision_at: Optional[datetime] = None
    updated_at: datetime


class CaseResponse(BaseModel):
    id: str
    case_name: Optional[str] = None
    pipeline_status: Dict[str, str] = {}
    pipeline_errors: Dict[str, dict] = {}
    documents: dict = {}
    # Human decision
    decision: Optional[str] = None  # approved | review | declined
    decision_by: Optional[str] = None
    decision_at: Optional[datetime] = None
    decision_comment: Optional[str] = None
    # Timestamps
    created_at: datetime
    updated_at: datetime


class CaseListResponse(BaseModel):
    cases: List[CaseResponse]


# ─── Dashboard summary (enriched case list) ───────────────────────────────────

class CaseDashboardSummary(BaseModel):
    """Enriched case data for dashboard display."""
    # Core case fields
    id: str
    case_name: Optional[str] = None
    created_at: datetime
    pipeline_status: Dict[str, str] = {}
    decision: Optional[str] = None  # approved | review | declined

    # Risk
    risk_level: Optional[str] = None  # "High" | "Intermediate" | "Low"

    # Test verification
    tests_required: Optional[int] = None
    tests_found: Optional[int] = None

    # MER confidence
    mer_high_confidence_pct: Optional[float] = None  # e.g., 95.0
    mer_low_confidence_count: Optional[int] = None

    # Face match
    face_match_decision: Optional[str] = None  # "match" | "no_match" | "unclear"

    # Location check
    location_check_decision: Optional[str] = None  # "pass" | "needs_review" | "fail" | "insufficient"

    # Computed flag
    needs_attention: bool = False


class CaseDashboardResponse(BaseModel):
    """Response for dashboard case list."""
    cases: List[CaseDashboardSummary]
    # Aggregate stats
    total: int
    awaiting_decision: int
    decided: int
    needs_attention_count: int
    high_risk_count: int


# ─── Process-all response ────────────────────────────────────────────────────

class PipelineResult(BaseModel):
    pipeline: str
    status: str
    error: str = None
    fields_count: int = None
    version: int = None


class ProcessAllResponse(BaseModel):
    case_id: str
    pipelines_triggered: List[str]
    pipelines_skipped: List[str]
    results: Dict[str, Any]


# ─── Decision (human underwriter) ─────────────────────────────────────────────

class DecisionRequest(BaseModel):
    """Request to set case decision."""
    decision: str  # approved | review | declined
    comment: Optional[str] = None


class DecisionResponse(BaseModel):
    """Response after setting case decision."""
    case_id: str
    decision: str
    decision_by: str
    decision_at: datetime
    decision_comment: Optional[str] = None
    message: str


# ─── Delete case ───────────────────────────────────────────────────────────────

class CaseDeleteResponse(BaseModel):
    """Response after soft-deleting a case."""
    case_id: str
    message: str
