import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.recommendation_service.database import create_tables, get_session
from services.recommendation_service.redis_client import close_redis, connect_redis
from services.recommendation_service.schemas import (
    ReactionCreate,
    ReactionResult,
    RecommendationResponse,
    RefreshResult,
)
from services.recommendation_service.service import (
    get_next_recommendation,
    refresh_feed,
    register_reaction,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    await create_tables()
    await connect_redis()
    logger.info("Recommendation service started")
    yield
    await close_redis()
    logger.info("Recommendation service stopped")


app = FastAPI(title="Recommendation Service", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/recommendations/{viewer_id}/next", response_model=RecommendationResponse)
async def read_next_recommendation(
    viewer_id: int, session: AsyncSession = Depends(get_session)
) -> RecommendationResponse:
    try:
        recommendation = await get_next_recommendation(session, viewer_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if recommendation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подходящих анкет пока нет. Попробуй позже.",
        )
    return recommendation


@app.post("/recommendations/{viewer_id}/reaction", response_model=ReactionResult)
async def create_reaction(
    viewer_id: int,
    body: ReactionCreate,
    session: AsyncSession = Depends(get_session),
) -> ReactionResult:
    try:
        next_recommendation = await register_reaction(
            session,
            viewer_id,
            body.target_account_id,
            body.reaction_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ReactionResult(accepted=True, next_recommendation=next_recommendation)


@app.post("/recommendations/{viewer_id}/refresh", response_model=RefreshResult)
async def rebuild_feed(
    viewer_id: int, session: AsyncSession = Depends(get_session)
) -> RefreshResult:
    try:
        cached_items = await refresh_feed(session, viewer_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return RefreshResult(refreshed=True, cached_items=cached_items)
