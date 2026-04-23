from sqlalchemy.ext.asyncio import AsyncSession

from services.recommendation_service.config import settings
from services.recommendation_service.crud import (
    get_anketa,
    get_behavioral_stats,
    get_candidate_anketas,
    get_viewed_ids,
    save_reaction,
)
from services.recommendation_service.ranking import (
    BehavioralStats,
    calculate_behavioral_score,
    calculate_compatibility_score,
    calculate_final_score,
    calculate_primary_score,
)
from services.recommendation_service.redis_client import get_redis
from services.recommendation_service.schemas import RecommendationResponse, ScoreBreakdown


def _feed_key(viewer_id: int) -> str:
    return f"recommendations:{viewer_id}"


def _serialize_recommendation(anketa, scores: ScoreBreakdown) -> RecommendationResponse:
    return RecommendationResponse(
        account_id=anketa.account_id,
        display_name=anketa.display_name,
        age=anketa.age,
        gender=anketa.gender,
        city=anketa.city,
        about=anketa.about,
        want_gender=anketa.want_gender,
        want_age_min=anketa.want_age_min,
        want_age_max=anketa.want_age_max,
        want_city=anketa.want_city,
        visible=anketa.visible,
        photo_count=anketa.photo_count,
        scores=scores,
    )


async def build_feed(session: AsyncSession, viewer_id: int) -> list[int]:
    viewer = await get_anketa(session, viewer_id)
    if viewer is None:
        raise ValueError("Сначала создай анкету, чтобы получать рекомендации.")
    if not viewer.profile_completed:
        raise ValueError("Заполни анкету до конца, чтобы мы могли подобрать рекомендации.")

    excluded_ids = await get_viewed_ids(session, viewer_id)
    candidates = list(await get_candidate_anketas(session, viewer_id, excluded_ids))
    if not candidates:
        return []

    behavioral_map = await get_behavioral_stats(
        session, [candidate.account_id for candidate in candidates]
    )

    scored_candidates: list[tuple[float, int]] = []
    for candidate in candidates:
        if not candidate.profile_completed:
            continue
        primary_score = calculate_primary_score(candidate)
        compatibility_score = calculate_compatibility_score(viewer, candidate)
        stats = behavioral_map.get(candidate.account_id, {"like": 0, "skip": 0})
        behavioral_score = calculate_behavioral_score(
            BehavioralStats(likes=stats["like"], skips=stats["skip"])
        )
        final_score = calculate_final_score(
            primary_score,
            compatibility_score,
            behavioral_score,
        )
        scored_candidates.append((final_score, candidate.account_id))

    scored_candidates.sort(key=lambda item: item[0], reverse=True)
    return [account_id for _, account_id in scored_candidates[: settings.FEED_SIZE]]


async def refresh_feed(session: AsyncSession, viewer_id: int) -> int:
    redis = get_redis()
    key = _feed_key(viewer_id)
    await redis.delete(key)

    candidate_ids = await build_feed(session, viewer_id)
    if candidate_ids:
        await redis.rpush(key, *candidate_ids)
        await redis.expire(key, 3600)
    return len(candidate_ids)


async def get_next_recommendation(
    session: AsyncSession, viewer_id: int
) -> RecommendationResponse | None:
    redis = get_redis()
    key = _feed_key(viewer_id)

    if await redis.llen(key) == 0:
        await refresh_feed(session, viewer_id)

    while True:
        next_account_id = await redis.lpop(key)
        if next_account_id is None:
            return None

        anketa = await get_anketa(session, int(next_account_id))
        viewer = await get_anketa(session, viewer_id)
        if anketa is None or viewer is None:
            continue

        primary_score = calculate_primary_score(anketa)
        compatibility_score = calculate_compatibility_score(viewer, anketa)
        stats_map = await get_behavioral_stats(session, [anketa.account_id])
        stats = stats_map.get(anketa.account_id, {"like": 0, "skip": 0})
        behavioral_score = calculate_behavioral_score(
            BehavioralStats(likes=stats["like"], skips=stats["skip"])
        )
        final_score = calculate_final_score(
            primary_score,
            compatibility_score,
            behavioral_score,
        )

        return _serialize_recommendation(
            anketa,
            ScoreBreakdown(
                primary_score=primary_score,
                compatibility_score=compatibility_score,
                behavioral_score=behavioral_score,
                final_score=final_score,
            ),
        )


async def register_reaction(
    session: AsyncSession, viewer_id: int, target_account_id: int, reaction_type: str
) -> RecommendationResponse | None:
    await save_reaction(session, viewer_id, target_account_id, reaction_type)
    return await get_next_recommendation(session, viewer_id)

