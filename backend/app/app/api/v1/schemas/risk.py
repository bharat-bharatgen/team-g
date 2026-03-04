from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


# ─── Source version info ─────────────────────────────────────────────────────

class BasedOnInfo(BaseModel):
    """Information about which source versions were used for analysis."""
    mer_version: Optional[int] = None
    pathology_version: Optional[int] = None
    source_freshness: int


# ─── Result response ─────────────────────────────────────────────────────────

class RiskResultResponse(BaseModel):
    """Full risk analysis result with citation references."""
    id: str
    case_id: str
    version: int
    based_on: BasedOnInfo
    patient_info: Dict[str, Any]
    critical_flags: List[Dict[str, Any]]
    contradictions: List[Dict[str, Any]]
    llm_response: Dict[str, Any]
    references: Dict[str, Dict[str, Any]] = {}  # ref_id -> source info for citations
    created_at: datetime


# ─── Version list ────────────────────────────────────────────────────────────

class RiskVersionEntry(BaseModel):
    """Entry for version listing."""
    id: str
    version: int
    mer_version: Optional[int] = None
    pathology_version: Optional[int] = None
    source_freshness: int
    risk_level: Optional[str] = None  # High | Intermediate | Low
    created_at: datetime


class RiskVersionsResponse(BaseModel):
    """List of all risk analysis versions for a case."""
    case_id: str
    versions: List[RiskVersionEntry]


# ─── Cited item for structured citations ─────────────────────────────────────

class CitedItem(BaseModel):
    """Item with text and reference IDs for citation linking."""
    text: str
    refs: List[str] = []


# ─── Summary response (for quick polling) ────────────────────────────────────

class RiskSummaryResponse(BaseModel):
    """Quick summary of risk analysis result for human decision makers."""
    case_id: str
    version: int
    based_on: BasedOnInfo
    red_flags: List[Any] = []  # Can be strings (old) or CitedItem dicts (new)
    contradictions: List[Any] = []  # Can be strings (old) or CitedItem dicts (new)
    summary: Optional[str] = None
    risk_level: Optional[str] = None  # High | Intermediate | Low
    created_at: datetime
