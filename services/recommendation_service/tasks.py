import asyncio
import logging

from services.recommendation_service.celery_app import celery_app
from services.recommendation_service.config import settings
from services.recommendation_service.crud import get_recent_viewer_ids, purge_old_reactions
from services.recommendation_service.database import AsyncSessionFactory, create_tables, optimize_database
from services.recommendation_service.redis_client import close_redis, connect_redis
from services.recommendation_service.service import refresh_feed

logger = logging.getLogger(__name__)


@celery_app.task(name="services.recommendation_service.tasks.refresh_active_feeds")
def refresh_active_feeds() -> dict[str, int]:
    return asyncio.run(_refresh_active_feeds())


async def _refresh_active_feeds() -> dict[str, int]:
    await create_tables()
    await optimize_database()
    await connect_redis()
    refreshed = 0
    skipped = 0

    try:
        async with AsyncSessionFactory() as session:
            viewer_ids = await get_recent_viewer_ids(session, settings.FEED_WARM_VIEWERS_LIMIT)
            for viewer_id in viewer_ids:
                try:
                    await refresh_feed(session, viewer_id)
                    refreshed += 1
                except ValueError:
                    skipped += 1
        logger.info("refresh_active_feeds completed: refreshed=%s skipped=%s", refreshed, skipped)
        return {"refreshed": refreshed, "skipped": skipped}
    finally:
        await close_redis()


@celery_app.task(name="services.recommendation_service.tasks.cleanup_old_reactions")
def cleanup_old_reactions() -> dict[str, int]:
    return asyncio.run(_cleanup_old_reactions())


async def _cleanup_old_reactions() -> dict[str, int]:
    await create_tables()
    await optimize_database()

    async with AsyncSessionFactory() as session:
        deleted = await purge_old_reactions(session, settings.REACTION_RETENTION_DAYS)
    logger.info("cleanup_old_reactions completed: deleted=%s", deleted)
    return {"deleted": deleted}
