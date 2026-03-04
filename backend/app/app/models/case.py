from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class PipelineStage(str, Enum):
    NOT_STARTED = "not_started"
    PROCESSING = "processing"
    EXTRACTED = "extracted"
    REVIEWED = "reviewed"
    FAILED = "failed"


class DocumentType(str, Enum):
    MER = "mer"
    PATHOLOGY = "pathology"
    PHOTO = "photo"
    ID_PROOF = "id_proof"


class FileStatus(str, Enum):
    PENDING = "pending"
    UPLOADED = "uploaded"


class CaseDecision(str, Enum):
    APPROVED = "approved"
    REVIEW = "review"
    DECLINED = "declined"


class FileEntry(BaseModel):
    id: str
    file_name: str
    s3_key: str
    content_type: str
    status: FileStatus = FileStatus.PENDING
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


def _default_pipeline_status() -> Dict[str, str]:
    return {
        "mer": PipelineStage.NOT_STARTED,
        "pathology": PipelineStage.NOT_STARTED,
        "risk": PipelineStage.NOT_STARTED,
        "face_match": PipelineStage.NOT_STARTED,
        "location_check": PipelineStage.NOT_STARTED,
        "test_verification": PipelineStage.NOT_STARTED,
    }


def _default_pipeline_errors() -> Dict[str, dict]:
    return {}


class CaseModel(BaseModel):
    user_id: str
    case_name: Optional[str] = None
    pipeline_status: Dict[str, str] = Field(default_factory=_default_pipeline_status)
    pipeline_errors: Dict[str, dict] = Field(default_factory=_default_pipeline_errors)
    documents: Dict[DocumentType, List[FileEntry]] = Field(default_factory=dict)
    # Human decision fields
    decision: Optional[str] = None  # approved | review | declined
    decision_by: Optional[str] = None
    decision_at: Optional[datetime] = None
    decision_comment: Optional[str] = None
    # Soft delete
    is_deleted: bool = False
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
