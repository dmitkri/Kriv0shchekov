from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

GenderOption = Literal["Мужчина", "Женщина", "Другое"]
PreferenceGenderOption = Literal["Мужчина", "Женщина", "Другое", "Не важно"]


class AnketaUpsert(BaseModel):
    display_name: str = Field(min_length=2, max_length=100)
    age: int = Field(ge=18, le=100)
    gender: GenderOption
    city: str = Field(min_length=2, max_length=100)
    about: str = Field(min_length=10, max_length=500)
    want_gender: PreferenceGenderOption
    want_age_min: int = Field(ge=18, le=100)
    want_age_max: int = Field(ge=18, le=100)
    want_city: str = Field(min_length=2, max_length=100)
    visible: bool = True

    @model_validator(mode="after")
    def validate_age_range(self) -> "AnketaUpsert":
        if self.want_age_max < self.want_age_min:
            raise ValueError("want_age_max must be greater than or equal to want_age_min")
        return self


class AnketaResponse(BaseModel):
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
    created_at: datetime
    updated_at: datetime
    profile_completed: bool

    model_config = {"from_attributes": True}

