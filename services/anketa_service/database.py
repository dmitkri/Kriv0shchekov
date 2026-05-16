from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.anketa_service.config import settings
from services.anketa_service.models import Base

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)

PHOTO_MIGRATIONS = (
    """
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'anketas' AND column_name = 'photo_file_ids'
        ) THEN
            INSERT INTO photos (anketa_account_id, file_key, position)
            SELECT
                anketas.account_id,
                photo_key.file_key,
                photo_key.position - 1
            FROM anketas
            CROSS JOIN LATERAL unnest(photo_file_ids) WITH ORDINALITY AS photo_key(file_key, position)
            WHERE COALESCE(array_length(photo_file_ids, 1), 0) > 0
              AND NOT EXISTS (
                  SELECT 1
                  FROM photos
                  WHERE photos.anketa_account_id = anketas.account_id
              );
        END IF;
    END $$;
    """,
    """
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'anketas' AND column_name = 'photo_keys'
        ) THEN
            INSERT INTO photos (anketa_account_id, file_key, position)
            SELECT
                anketas.account_id,
                photo_key.file_key,
                photo_key.position - 1
            FROM anketas
            CROSS JOIN LATERAL unnest(photo_keys) WITH ORDINALITY AS photo_key(file_key, position)
            WHERE COALESCE(array_length(photo_keys, 1), 0) > 0
              AND NOT EXISTS (
                  SELECT 1
                  FROM photos
                  WHERE photos.anketa_account_id = anketas.account_id
              );
        END IF;
    END $$;
    """,
    """
    UPDATE anketas
    SET photo_count = COALESCE(
        (
            SELECT COUNT(*)
            FROM photos
            WHERE photos.anketa_account_id = anketas.account_id
        ),
        0
    )
    """,
)


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for statement in PHOTO_MIGRATIONS:
            await conn.execute(text(statement))


async def get_session() -> AsyncSession:
    async with AsyncSessionFactory() as session:
        yield session
