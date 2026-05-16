import logging
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


class PhotoAPIClient:
    def __init__(self, base_url: str, session: aiohttp.ClientSession) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session

    async def upload_photo(
        self,
        content: bytes,
        filename: str,
        content_type: str,
    ) -> Optional[str]:
        form = aiohttp.FormData()
        form.add_field(
            "file",
            content,
            filename=filename,
            content_type=content_type,
        )
        try:
            async with self._session.post(
                f"{self._base_url}/photos/upload",
                data=form,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("file_key")
                text = await resp.text()
                logger.error("upload_photo failed: status=%d body=%s", resp.status, text)
                return None
        except aiohttp.ClientError as exc:
            logger.error("upload_photo failed: %s", exc)
            return None

    async def get_photo(self, file_key: str) -> tuple[bytes | None, str | None]:
        try:
            async with self._session.get(f"{self._base_url}/photos/{file_key}") as resp:
                if resp.status == 200:
                    return await resp.read(), resp.headers.get("Content-Type")
                logger.warning("get_photo unexpected status: %d", resp.status)
                return None, None
        except aiohttp.ClientError as exc:
            logger.error("get_photo failed: %s", exc)
            return None, None

    async def delete_photo(self, file_key: str) -> bool:
        try:
            async with self._session.delete(f"{self._base_url}/photos/{file_key}") as resp:
                if resp.status == 204:
                    return True
                logger.warning("delete_photo unexpected status: %d", resp.status)
                return False
        except aiohttp.ClientError as exc:
            logger.error("delete_photo failed: %s", exc)
            return False
