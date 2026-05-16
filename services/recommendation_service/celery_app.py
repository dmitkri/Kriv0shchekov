from celery import Celery

from services.recommendation_service.config import settings

celery_app = Celery(
    "recommendation_service",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=False,
    beat_schedule={
        "refresh-active-feeds": {
            "task": "services.recommendation_service.tasks.refresh_active_feeds",
            "schedule": settings.FEED_REFRESH_INTERVAL_SEC,
        },
        "cleanup-old-reactions-daily": {
            "task": "services.recommendation_service.tasks.cleanup_old_reactions",
            "schedule": 24 * 60 * 60,
        },
    },
)

celery_app.autodiscover_tasks(["services.recommendation_service"])
