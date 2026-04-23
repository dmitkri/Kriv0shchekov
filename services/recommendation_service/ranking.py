from dataclasses import dataclass

from services.recommendation_service.models import Anketa


@dataclass(slots=True)
class BehavioralStats:
    likes: int = 0
    skips: int = 0


def _normalize_score(raw_score: float, max_score: float) -> float:
    if max_score <= 0:
        return 0.0
    return round(raw_score / max_score, 4)


def calculate_primary_score(candidate: Anketa) -> float:
    score = 0.0
    if candidate.display_name:
        score += 1
    if candidate.city:
        score += 1
    if candidate.about and len(candidate.about) >= 20:
        score += 1
    if candidate.want_gender and candidate.want_city:
        score += 1
    if candidate.photo_count > 0:
        score += 1
    return _normalize_score(score, 5)


def _match_gender(preferred_gender: str, actual_gender: str) -> bool:
    return preferred_gender == "Не важно" or preferred_gender == actual_gender


def _match_city(preferred_city: str, actual_city: str) -> bool:
    return preferred_city == "Не важно" or preferred_city.casefold() == actual_city.casefold()


def calculate_compatibility_score(viewer: Anketa, candidate: Anketa) -> float:
    score = 0.0
    if _match_gender(viewer.want_gender, candidate.gender):
        score += 1
    if viewer.want_age_min <= candidate.age <= viewer.want_age_max:
        score += 1
    if _match_city(viewer.want_city, candidate.city):
        score += 1
    if _match_gender(candidate.want_gender, viewer.gender):
        score += 1
    if candidate.want_age_min <= viewer.age <= candidate.want_age_max:
        score += 1
    if _match_city(candidate.want_city, viewer.city):
        score += 1
    return _normalize_score(score, 6)


def calculate_behavioral_score(stats: BehavioralStats) -> float:
    total = stats.likes + stats.skips
    if total == 0:
        return 0.5
    return round(stats.likes / total, 4)


def calculate_final_score(
    primary_score: float,
    compatibility_score: float,
    behavioral_score: float,
) -> float:
    final_score = primary_score * 0.35 + compatibility_score * 0.45 + behavioral_score * 0.20
    return round(final_score, 4)

