from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/dating"
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    LOG_LEVEL: str = "INFO"
    FEED_SIZE: int = 10
    FEED_CANDIDATE_POOL: int = 200
    FEED_REDIS_TTL_SEC: int = 3600
    FEED_REFRESH_INTERVAL_SEC: int = 900
    FEED_WARM_VIEWERS_LIMIT: int = 200
    REACTION_RETENTION_DAYS: int = 90


settings = Settings()
