from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from services.anketa_service.models import Anketa, Photo
from services.anketa_service.schemas import AnketaUpsert


async def get_anketa(session: AsyncSession, account_id: int) -> Anketa | None:
    result = await session.execute(
        select(Anketa)
        .options(selectinload(Anketa.photos))
        .where(Anketa.account_id == account_id)
    )
    return result.scalar_one_or_none()


async def list_anketas(
    session: AsyncSession, limit: int = 100, offset: int = 0
) -> Sequence[Anketa]:
    result = await session.execute(
        select(Anketa)
        .options(selectinload(Anketa.photos))
        .order_by(Anketa.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def upsert_anketa(
    session: AsyncSession, account_id: int, payload: AnketaUpsert
) -> Anketa:
    anketa = await get_anketa(session, account_id)
    if anketa is None:
        anketa = Anketa(account_id=account_id, photo_count=0)
        session.add(anketa)

    anketa.display_name = payload.display_name
    anketa.age = payload.age
    anketa.gender = payload.gender
    anketa.city = payload.city
    anketa.about = payload.about
    anketa.want_gender = payload.want_gender
    anketa.want_age_min = payload.want_age_min
    anketa.want_age_max = payload.want_age_max
    anketa.want_city = payload.want_city
    anketa.photos.clear()
    anketa.photos.extend(
        Photo(file_key=file_key, position=index)
        for index, file_key in enumerate(payload.photo_keys)
    )
    anketa.photo_count = len(payload.photo_keys)
    anketa.visible = payload.visible

    await session.commit()
    return await get_anketa(session, account_id) or anketa
