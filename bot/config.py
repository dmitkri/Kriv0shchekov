from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    TELEGRAM_BOT_TOKEN: str
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    REDIS_URL: str = "redis://localhost:6379/0"
    USER_SERVICE_URL: str = "http://user_service:8000"
    ANKETA_SERVICE_URL: str = "http://anketa_service:8001"
    RECOMMENDATION_SERVICE_URL: str = "http://recommendation_service:8002"
    PHOTO_SERVICE_URL: str = "http://photo_service:8003"
    LOG_LEVEL: str = "INFO"


settings = Settings()
