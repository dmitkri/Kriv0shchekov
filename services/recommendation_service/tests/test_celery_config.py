import unittest

try:
    from services.recommendation_service.celery_app import celery_app
    from services.recommendation_service.config import settings
except ModuleNotFoundError:  # pragma: no cover
    celery_app = None
    settings = None


@unittest.skipIf(celery_app is None, "celery is not installed in current environment")
class CeleryConfigTests(unittest.TestCase):
    def test_refresh_schedule_exists(self) -> None:
        schedule = celery_app.conf.beat_schedule
        self.assertIn("refresh-active-feeds", schedule)
        self.assertEqual(
            schedule["refresh-active-feeds"]["task"],
            "services.recommendation_service.tasks.refresh_active_feeds",
        )
        self.assertEqual(
            schedule["refresh-active-feeds"]["schedule"],
            settings.FEED_REFRESH_INTERVAL_SEC,
        )

    def test_cleanup_schedule_exists(self) -> None:
        schedule = celery_app.conf.beat_schedule
        self.assertIn("cleanup-old-reactions-daily", schedule)
        self.assertEqual(
            schedule["cleanup-old-reactions-daily"]["task"],
            "services.recommendation_service.tasks.cleanup_old_reactions",
        )


if __name__ == "__main__":
    unittest.main()
