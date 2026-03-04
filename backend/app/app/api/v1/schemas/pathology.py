from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


# ─── Result response ─────────────────────────────────────────────────────────

class PathologyFieldResponse(BaseModel):
    id: str
    key: str
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None   # Range from report
    config_range: Optional[str] = None      # Range from config (NEW_PARAMS)
    range_status: Optional[str] = None      # "normal" | "abnormal" | null
    flag: Optional[str] = None              # From LLM (deprecated, use range_status)
    method: Optional[str] = None
    reference_name: Optional[str] = None
    sample_type: Optional[str] = None       # "blood" | "urine" | "stool" | null
    page_number: Optional[int] = None       # Source page in the PDF document (1-indexed)
    section_path: List[str] = []
    is_standard: bool = True
    source: str


class PathologyResultResponse(BaseModel):
    id: str
    case_id: str
    version: int
    source: str
    patient_info: Dict[str, Any]
    lab_info: Dict[str, Any]
    report_info: Dict[str, Any]
    fields: List[PathologyFieldResponse]
    created_at: datetime


# ─── Summary response ─────────────────────────────────────────────────────────

class PathologySummaryResponse(BaseModel):
    """Summary statistics for pathology results."""
    case_id: str
    version: int
    total: int              # Total params extracted
    normal_count: int       # Params in normal range
    abnormal_count: int     # Params out of range
    no_range_count: int     # Params with no range to compare


# ─── Version list ─────────────────────────────────────────────────────────────

class PathologyVersionEntry(BaseModel):
    id: str
    version: int
    source: str
    created_at: datetime


class PathologyVersionsResponse(BaseModel):
    case_id: str
    versions: List[PathologyVersionEntry]


# ─── Excel import response ───────────────────────────────────────────────────

class PathologyImportResponse(BaseModel):
    id: str
    case_id: str
    version: int
    source: str
    fields_count: int
    changed_fields: int
    message: str
