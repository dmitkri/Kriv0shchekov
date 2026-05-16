import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, File, HTTPException, Response, UploadFile, status
from minio.error import S3Error

from services.photo_service.schemas import PhotoUploadResponse
from services.photo_service.storage import storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    last_error: Exception | None = None
    for _ in range(20):
        try:
            await asyncio.to_thread(storage.ensure_bucket)
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            await asyncio.sleep(1)
    else:
        raise RuntimeError(f"Photo service failed to connect to MinIO: {last_error}") from last_error

    logger.info("Photo service started")
    yield
    logger.info("Photo service stopped")


app = FastAPI(title="Photo Service", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/photos/upload", response_model=PhotoUploadResponse)
async def upload_photo(file: UploadFile = File(...)) -> PhotoUploadResponse:
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл пустой.",
        )

    filename = file.filename or "photo.jpg"
    content_type = file.content_type or "image/jpeg"
    try:
        file_key = await asyncio.to_thread(
            storage.upload_photo,
            content,
            filename,
            content_type,
        )
    except S3Error as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Не удалось сохранить фото: {exc}",
        ) from exc

    return PhotoUploadResponse(
        file_key=file_key,
        content_type=content_type,
        size=len(content),
    )


@app.get("/photos/{file_key}")
async def read_photo(file_key: str) -> Response:
    try:
        content, content_type = await asyncio.to_thread(storage.get_photo, file_key)
    except S3Error as exc:
        if exc.code == "NoSuchKey":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Фото не найдено.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Не удалось получить фото: {exc}",
        ) from exc

    return Response(content=content, media_type=content_type)


@app.delete("/photos/{file_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(file_key: str) -> Response:
    try:
        await asyncio.to_thread(storage.delete_photo, file_key)
    except S3Error as exc:
        if exc.code != "NoSuchKey":
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Не удалось удалить фото: {exc}",
            ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
