import logging
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)


class AnketaAPIClient:
    def __init__(self, base_url: str, session: aiohttp.ClientSession) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session

    async def get_anketa(self, account_id: int) -> Optional[dict[str, Any]]:
        try:
            async with self._session.get(
                f"{self._base_url}/anketas/{account_id}"
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                if resp.status == 404:
                    return None
                logger.warning("get_anketa unexpected status: %d", resp.status)
                return None
        except aiohttp.ClientError as exc:
            logger.error("get_anketa failed: %s", exc)
            return None

    async def save_anketa(
        self, account_id: int, payload: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        try:
            async with self._session.put(
                f"{self._base_url}/anketas/{account_id}", json=payload
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                text = await resp.text()
                logger.error("save_anketa failed: status=%d body=%s", resp.status, text)
                return None
        except aiohttp.ClientError as exc:
            logger.error("save_anketa failed: %s", exc)
            return None

