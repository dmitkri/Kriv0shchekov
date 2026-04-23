from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.recommendation_service.models import Anketa, ProfileReaction


async def get_anketa(session: AsyncSession, account_id: int) -> Anketa | None:
    result = await session.execute(
        select(Anketa).where(Anketa.account_id == account_id)
    )
    return result.scalar_one_or_none()


async def get_candidate_anketas(
    session: AsyncSession, viewer_id: int, excluded_ids: set[int]
) -> Sequence[Anketa]:
    stmt = select(Anketa).where(
        Anketa.account_id != viewer_id,
        Anketa.visible.is_(True),
    )
    if excluded_ids:
        stmt = stmt.where(~Anketa.account_id.in_(excluded_ids))
    result = await session.execute(stmt.order_by(Anketa.updated_at.desc()))
    return result.scalars().all()


async def get_viewed_ids(session: AsyncSession, viewer_id: int) -> set[int]:
    result = await session.execute(
        select(ProfileReaction.target_account_id).where(ProfileReaction.viewer_id == viewer_id)
    )
    return {value for value in result.scalars().all()}


async def save_reaction(
    session: AsyncSession,
    viewer_id: int,
    target_account_id: int,
    reaction_type: str,
) -> ProfileReaction:
    result = await session.execute(
        select(ProfileReaction).where(
            ProfileReaction.viewer_id == viewer_id,
            ProfileReaction.target_account_id == target_account_id,
        )
    )
    reaction = result.scalar_one_or_none()
    if reaction is None:
        reaction = ProfileReaction(
            viewer_id=viewer_id,
            target_account_id=target_account_id,
            reaction_type=reaction_type,
        )
        session.add(reaction)
    else:
        reaction.reaction_type = reaction_type

    await session.commit()
    await session.refresh(reaction)
    return reaction


async def get_behavioral_stats(
    session: AsyncSession, candidate_ids: list[int]
) -> dict[int, dict[str, int]]:
    if not candidate_ids:
        return {}

    result = await session.execute(
        select(
            ProfileReaction.target_account_id,
            ProfileReaction.reaction_type,
            func.count(ProfileReaction.id),
        )
        .where(ProfileReaction.target_account_id.in_(candidate_ids))
        .group_by(ProfileReaction.target_account_id, ProfileReaction.reaction_type)
    )

    stats: dict[int, dict[str, int]] = {}
    for target_account_id, reaction_type, count in result.all():
        entry = stats.setdefault(int(target_account_id), {"like": 0, "skip": 0})
        entry[str(reaction_type)] = int(count)
    return stats
