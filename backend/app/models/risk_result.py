from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RiskResultModel(BaseModel):
    """Risk analysis result with source version tracking and citation references."""
    case_id: str
    version: int = 1

    # Source versions used for this analysis
    mer_version: Optional[int] = None       # null if MER not uploaded
    pathology_version: Optional[int] = None  # null if pathology not uploaded
    source_freshness: int = 0               # (mer_version or 0) + (pathology_version or 0)

    # Pre-computed data from pre-processing
    patient_info: Dict[str, Any] = Field(default_factory=dict)
    critical_flags: List[Dict[str, Any]] = Field(default_factory=list)
    contradictions: List[Dict[str, Any]] = Field(default_factory=list)

    # LLM analysis response
    llm_response: Dict[str, Any] = Field(default_factory=dict)

    # Reference lookup for citations (ref_id -> source info)
    # e.g., {"PATH:HbA1c": {"source": "pathology", "param": "HbA1c", ...}}
    references: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)
