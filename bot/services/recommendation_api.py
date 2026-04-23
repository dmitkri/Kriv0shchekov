import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class RecommendationAPIClient:
    def __init__(self, base_url: str, session: aiohttp.ClientSession) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session

    async def get_next_recommendation(
        self, viewer_id: int
    ) -> tuple[dict[str, Any] | None, str | None]:
        try:
            async with self._session.get(
                f"{self._base_url}/recommendations/{viewer_id}/next"
            ) as resp:
                if resp.status == 200:
                    return await resp.json(), None
                return None, await _extract_error(resp)
        except aiohttp.ClientError as exc:
            logger.error("get_next_recommendation failed: %s", exc)
            return None, "Сервис рекомендаций сейчас недоступен."

    async def submit_reaction(
        self, viewer_id: int, target_account_id: int, reaction_type: str
    ) -> tuple[dict[str, Any] | None, str | None]:
        payload = {
            "target_account_id": target_account_id,
            "reaction_type": reaction_type,
        }
        try:
            async with self._session.post(
                f"{self._base_url}/recommendations/{viewer_id}/reaction",
                json=payload,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("next_recommendation"), None
                return None, await _extract_error(resp)
        except aiohttp.ClientError as exc:
            logger.error("submit_reaction failed: %s", exc)
            return None, "Не удалось сохранить реакцию."

    async def refresh_feed(self, viewer_id: int) -> bool:
        try:
            async with self._session.post(
                f"{self._base_url}/recommendations/{viewer_id}/refresh"
            ) as resp:
                if resp.status == 200:
                    return True
                logger.warning("refresh_feed unexpected status: %d", resp.status)
                return False
        except aiohttp.ClientError as exc:
            logger.warning("refresh_feed failed: %s", exc)
            return False


async def _extract_error(resp: aiohttp.ClientResponse) -> str:
    try:
        data = await resp.json()
    except aiohttp.ContentTypeError:
        return await resp.text()
    detail = data.get("detail")
    if isinstance(detail, str):
        return detail
    return "Произошла ошибка при обращении к сервису рекомендаций."
