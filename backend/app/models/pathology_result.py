from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FieldSource(str, Enum):
    LLM = "llm"
    USER = "user"


class PathologyField(BaseModel):
    """A single flattened field for Excel export/import."""
    id: str
    key: str                            # standardized param name or unmatched test name
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None   # Range extracted from report
    config_range: Optional[str] = None      # Range from NEW_PARAMS config
    range_status: Optional[str] = None      # "normal" | "abnormal" | null (no range)
    flag: Optional[str] = None              # "low" | "high" | "normal" | null (from LLM)
    method: Optional[str] = None
    reference_name: Optional[str] = None    # original name from report
    sample_type: Optional[str] = None       # "blood" | "urine" | "stool" | null
    page_number: Optional[int] = None       # source page in the document (1-indexed)
    section_path: List[str] = Field(default_factory=list)  # for unmatched tests
    is_standard: bool = True                # True for standard params, False for unmatched
    source: FieldSource = FieldSource.LLM


class PathologyResultModel(BaseModel):
    case_id: str
    version: int = 1
    source: str = "llm"                 # "llm" or "excel_import"

    # Raw LLM OCR output per page (step 1)
    pages: Dict[str, Any] = Field(default_factory=dict)

    # Merged metadata (best from across pages)
    patient_info: Dict[str, Any] = Field(default_factory=dict)
    lab_info: Dict[str, Any] = Field(default_factory=dict)
    report_info: Dict[str, Any] = Field(default_factory=dict)

    # Standardized output (step 2) — 50 params + unmatched_tests + Remark
    standardized: Dict[str, Any] = Field(default_factory=dict)

    # Flattened fields for Excel
    fields: List[PathologyField] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.utcnow)
