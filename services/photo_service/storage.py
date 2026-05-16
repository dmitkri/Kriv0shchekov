from __future__ import annotations

from io import BytesIO
from uuid import uuid4

from minio import Minio
from minio.error import S3Error

from services.photo_service.config import settings


class PhotoStorage:
    def __init__(self) -> None:
        self._client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self._bucket = settings.MINIO_BUCKET

    def ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def upload_photo(
        self,
        content: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        file_ext = ""
        if "." in filename:
            file_ext = filename.rsplit(".", 1)[-1].lower()
            file_ext = f".{file_ext}"

        object_name = f"{uuid4().hex}{file_ext}"
        data = BytesIO(content)
        self._client.put_object(
            self._bucket,
            object_name,
            data,
            length=len(content),
            content_type=content_type,
        )
        return object_name

    def get_photo(self, object_name: str) -> tuple[bytes, str]:
        response = self._client.get_object(self._bucket, object_name)
        try:
            content = response.read()
            content_type = response.headers.get("Content-Type", "application/octet-stream")
            return content, content_type
        finally:
            response.close()
            response.release_conn()

    def delete_photo(self, object_name: str) -> None:
        self._client.remove_object(self._bucket, object_name)


storage = PhotoStorage()

