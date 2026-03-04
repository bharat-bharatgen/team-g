from datetime import datetime
from typing import List
from pydantic import BaseModel
from app.models.case import DocumentType


class FileUploadRequest(BaseModel):
    file_name: str
    content_type: str


class UploadUrlRequest(BaseModel):
    document_type: DocumentType
    files: List[FileUploadRequest]


class FileUploadUrlResponse(BaseModel):
    file_id: str
    file_name: str
    upload_url: str


class UploadUrlResponse(BaseModel):
    document_type: DocumentType
    files: List[FileUploadUrlResponse]


class ConfirmUploadRequest(BaseModel):
    document_type: DocumentType
    file_ids: List[str]


class FileDetail(BaseModel):
    id: str
    file_name: str
    content_type: str
    url: str
    uploaded_at: datetime


class DocumentsResponse(BaseModel):
    documents: dict  # DocumentType -> List[FileDetail]

