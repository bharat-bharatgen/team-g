from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from app.api.v1.schemas.documents import (
    UploadUrlRequest,
    UploadUrlResponse,
    FileUploadUrlResponse,
    ConfirmUploadRequest,
    DocumentsResponse,
    FileDetail,
)
from app.models.case import FileEntry, FileStatus
from app.core.security import get_current_user
from app.dependencies import get_database
from app.services.storage import s3_service

router = APIRouter()

ALLOWED_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}


@router.post("/{case_id}/documents/upload-url", response_model=UploadUrlResponse)
async def get_upload_urls(case_id: str, body: UploadUrlRequest, user: dict = Depends(get_current_user)):
    db = await get_database()
    case = await db.cases.find_one({"_id": ObjectId(case_id), "user_id": user["id"]})
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    # Reject if document type already has files
    existing = case.get("documents", {}).get(body.document_type.value, [])
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{body.document_type.value} files already exist. Delete them first.",
        )

    # Validate content types
    for f in body.files:
        if f.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid content type: {f.content_type}. Allowed: pdf, jpeg, png",
            )

    file_responses = []
    file_entries = []

    for f in body.files:
        result = await s3_service.generate_upload_url(case_id, body.document_type.value, f.file_name, f.content_type)
        file_entries.append(
            FileEntry(
                id=result["file_id"],
                file_name=f.file_name,
                s3_key=result["s3_key"],
                content_type=f.content_type,
                status=FileStatus.PENDING,
            ).model_dump()
        )
        file_responses.append(
            FileUploadUrlResponse(
                file_id=result["file_id"],
                file_name=f.file_name,
                upload_url=result["upload_url"],
            )
        )

    # Store pending file entries in the case
    await db.cases.update_one(
        {"_id": ObjectId(case_id)},
        {
            "$set": {
                f"documents.{body.document_type.value}": file_entries,
                "updated_at": datetime.utcnow(),
            }
        },
    )

    return UploadUrlResponse(document_type=body.document_type, files=file_responses)


@router.post("/{case_id}/documents/confirm-upload")
async def confirm_upload(case_id: str, body: ConfirmUploadRequest, user: dict = Depends(get_current_user)):
    db = await get_database()
    case = await db.cases.find_one({"_id": ObjectId(case_id), "user_id": user["id"]})
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    doc_key = body.document_type.value
    files = case.get("documents", {}).get(doc_key, [])
    confirmed_ids = set(body.file_ids)

    updated = False
    for f in files:
        if f["id"] in confirmed_ids:
            f["status"] = FileStatus.UPLOADED.value
            updated = True

    if not updated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No matching pending files found")

    await db.cases.update_one(
        {"_id": ObjectId(case_id)},
        {"$set": {f"documents.{doc_key}": files, "updated_at": datetime.utcnow()}},
    )

    return {"message": "Upload confirmed"}


@router.get("/{case_id}/documents", response_model=DocumentsResponse)
async def list_documents(case_id: str, user: dict = Depends(get_current_user)):
    db = await get_database()
    case = await db.cases.find_one({"_id": ObjectId(case_id), "user_id": user["id"]})
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    documents = {}
    for doc_type, files in case.get("documents", {}).items():
        file_details = []
        for f in files:
            if f.get("status") == FileStatus.UPLOADED.value:
                url = await s3_service.generate_download_url(f["s3_key"])
                file_details.append(FileDetail(
                    id=f["id"],
                    file_name=f["file_name"],
                    content_type=f["content_type"],
                    url=url,
                    uploaded_at=f["uploaded_at"],
                ))
        documents[doc_type] = file_details

    return DocumentsResponse(documents=documents)


@router.delete("/{case_id}/documents/{document_type}")
async def delete_documents(case_id: str, document_type: str, user: dict = Depends(get_current_user)):
    db = await get_database()
    case = await db.cases.find_one({"_id": ObjectId(case_id), "user_id": user["id"]})
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    files = case.get("documents", {}).get(document_type, [])
    if not files:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No documents found for this type")

    # Delete from S3
    s3_keys = [f["s3_key"] for f in files]
    await s3_service.delete_files(s3_keys)

    # Remove from case
    await db.cases.update_one(
        {"_id": ObjectId(case_id)},
        {"$unset": {f"documents.{document_type}": ""}, "$set": {"updated_at": datetime.utcnow()}},
    )

    return {"message": f"Deleted {len(files)} file(s) for {document_type}"}
