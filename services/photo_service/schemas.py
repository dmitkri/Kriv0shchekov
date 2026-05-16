from pydantic import BaseModel


class PhotoUploadResponse(BaseModel):
    file_key: str
    content_type: str
    size: int

