import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from services.anketa_service.crud import get_anketa, list_anketas, upsert_anketa
from services.anketa_service.database import create_tables, get_session
from services.anketa_service.schemas import AnketaResponse, AnketaUpsert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    await create_tables()
    logger.info("Anketa service started")
    yield
    logger.info("Anketa service stopped")


app = FastAPI(title="Anketa Service", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/anketas/{account_id}", response_model=AnketaResponse)
async def read_anketa(
    account_id: int, session: AsyncSession = Depends(get_session)
) -> AnketaResponse:
    anketa = await get_anketa(session, account_id)
    if anketa is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anketa not found")
    return anketa


@app.put("/anketas/{account_id}", response_model=AnketaResponse)
async def save_anketa(
    account_id: int,
    body: AnketaUpsert,
    session: AsyncSession = Depends(get_session),
) -> AnketaResponse:
    return await upsert_anketa(session, account_id, body)


@app.get("/anketas", response_model=list[AnketaResponse])
async def read_anketas(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[AnketaResponse]:
    return list(await list_anketas(session, limit=limit, offset=offset))

