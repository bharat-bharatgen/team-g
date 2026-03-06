import uuid
import asyncio
from typing import List
import boto3
from app.config import settings


class S3Service:
    def __init__(self):
        client_kwargs = dict(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
        )
        if settings.s3_endpoint_url:
            client_kwargs["endpoint_url"] = settings.s3_endpoint_url
        self.s3_client = boto3.client("s3", **client_kwargs)
        self.bucket_name = settings.s3_bucket_name

    def _build_s3_key(self, case_id: str, document_type: str, file_id: str, file_name: str) -> str:
        ext = file_name.rsplit(".", 1)[-1] if "." in file_name else ""
        return f"insurance-copilot/{case_id}/{document_type}/{file_id}.{ext}" if ext else f"insurance-copilot/{case_id}/{document_type}/{file_id}"

    async def generate_upload_url(self, case_id: str, document_type: str, file_name: str, content_type: str) -> dict:
        """Generate a pre-signed PUT URL for frontend to upload directly to S3."""
        file_id = str(uuid.uuid4())
        s3_key = self._build_s3_key(case_id, document_type, file_id, file_name)

        upload_url = await asyncio.to_thread(
            self.s3_client.generate_presigned_url,
            "put_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": s3_key,
                "ContentType": content_type,
            },
            ExpiresIn=settings.s3_upload_url_expiry,
        )

        return {
            "file_id": file_id,
            "s3_key": s3_key,
            "upload_url": upload_url,
        }

    async def generate_download_url(self, s3_key: str) -> str:
        """Generate a pre-signed GET URL for frontend to view/download a file."""
        return await asyncio.to_thread(
            self.s3_client.generate_presigned_url,
            "get_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": s3_key,
            },
            ExpiresIn=settings.s3_download_url_expiry,
        )

    async def download_file(self, s3_key: str) -> bytes:
        """Download file content from S3 for backend processing."""
        response = await asyncio.to_thread(
            self.s3_client.get_object,
            Bucket=self.bucket_name,
            Key=s3_key,
        )
        return response["Body"].read()

    async def delete_files(self, s3_keys: List[str]) -> None:
        """Delete multiple files from S3."""
        if not s3_keys:
            return
        objects = [{"Key": key} for key in s3_keys]
        await asyncio.to_thread(
            self.s3_client.delete_objects,
            Bucket=self.bucket_name,
            Delete={"Objects": objects},
        )


s3_service = S3Service()
