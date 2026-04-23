from typing import Literal

from pydantic import BaseModel


class ScoreBreakdown(BaseModel):
    primary_score: float
    compatibility_score: float
    behavioral_score: float
    final_score: float


class RecommendationResponse(BaseModel):
    account_id: int
    display_name: str
    age: int
    gender: str
    city: str
    about: str
    want_gender: str
    want_age_min: int
    want_age_max: int
    want_city: str
    visible: bool
    photo_count: int
    scores: ScoreBreakdown


class ReactionCreate(BaseModel):
    target_account_id: int
    reaction_type: Literal["like", "skip"]


class ReactionResult(BaseModel):
    accepted: bool
    next_recommendation: RecommendationResponse | None = None


class RefreshResult(BaseModel):
    refreshed: bool
    cached_items: int

