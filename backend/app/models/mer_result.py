from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FieldSource(str, Enum):
    LLM = "llm"
    USER = "user"


class MERField(BaseModel):
    id: str
    page: int
    section: str                     # e.g. "header", "questions", "physical_measurement", etc.
    key: str                         # field label
    answer: Optional[str] = None     # primary value (Yes/No for Y/N fields, or text value for simple fields)
    details: Optional[str] = None    # additional details (for Y/N fields with extra info)
    confidence: Optional[float] = None  # None for null/missing values → no highlighting in frontend
    source: FieldSource = FieldSource.LLM


class MERResultModel(BaseModel):
    case_id: str
    version: int = 1
    source: str = "llm"             # "llm" or "excel_import"

    classification: Dict[str, Any] = Field(default_factory=dict)
    pages: Dict[str, Any] = Field(default_factory=dict)   # raw LLM JSON per page
    fields: List[MERField] = Field(default_factory=list)   # flattened fields

    created_at: datetime = Field(default_factory=datetime.utcnow)
