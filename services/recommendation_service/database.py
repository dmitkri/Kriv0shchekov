from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.recommendation_service.config import settings
from services.recommendation_service.models import ProfileReaction

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(ProfileReaction.metadata.create_all)


async def optimize_database() -> None:
    index_queries = (
        "CREATE INDEX IF NOT EXISTS ix_profile_reactions_viewer_created ON profile_reactions(viewer_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS ix_profile_reactions_target_reaction ON profile_reactions(target_account_id, reaction_type)",
        "CREATE INDEX IF NOT EXISTS ix_profile_reactions_created_at ON profile_reactions(created_at DESC)",
    )
    async with engine.begin() as conn:
        for query in index_queries:
            await conn.execute(text(query))


async def get_session() -> AsyncSession:
    async with AsyncSessionFactory() as session:
        yield session
