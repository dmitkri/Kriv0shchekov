import unittest
from dataclasses import dataclass

from services.recommendation_service.ranking import (
    BehavioralStats,
    calculate_behavioral_score,
    calculate_compatibility_score,
    calculate_final_score,
    calculate_primary_score,
)


@dataclass
class DummyAnketa:
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
    photo_count: int


def make_anketa(**overrides) -> DummyAnketa:
    payload = {
        "account_id": 1,
        "display_name": "Alice",
        "age": 25,
        "gender": "Ж",
        "city": "Moscow",
        "about": "Люблю спорт, книги и прогулки по вечерам.",
        "want_gender": "М",
        "want_age_min": 22,
        "want_age_max": 35,
        "want_city": "Moscow",
        "photo_count": 2,
    }
    payload.update(overrides)
    return DummyAnketa(**payload)


class RankingTests(unittest.TestCase):
    def test_primary_score_full_profile(self) -> None:
        anketa = make_anketa()
        self.assertEqual(calculate_primary_score(anketa), 1.0)

    def test_behavioral_score_without_reactions(self) -> None:
        score = calculate_behavioral_score(BehavioralStats(likes=0, skips=0))
        self.assertEqual(score, 0.5)

    def test_behavioral_score_with_reactions(self) -> None:
        score = calculate_behavioral_score(BehavioralStats(likes=8, skips=2))
        self.assertEqual(score, 0.8)

    def test_compatibility_score_perfect_match(self) -> None:
        viewer = make_anketa(account_id=10)
        candidate = make_anketa(
            account_id=11,
            gender="М",
            want_gender="Ж",
            age=27,
            want_age_min=20,
            want_age_max=30,
        )
        self.assertEqual(calculate_compatibility_score(viewer, candidate), 1.0)

    def test_final_score_weighted_formula(self) -> None:
        result = calculate_final_score(0.8, 0.9, 0.7)
        self.assertEqual(result, 0.825)


if __name__ == "__main__":
    unittest.main()
