#!/usr/bin/env python3
import argparse
import json
import sys
from copy import deepcopy
from typing import Any
from urllib import error, request


PROFILE_TEMPLATES: list[dict[str, Any]] = [
    {
        "display_name": "Анна",
        "username": "anna_seed",
        "age": 24,
        "gender": "Женщина",
        "city": "Москва",
        "about": "Люблю джаз, долгие прогулки и искать новые кофейни по выходным.",
        "want_gender": "Мужчина",
        "want_age_min": 24,
        "want_age_max": 33,
        "want_city": "Не важно",
    },
    {
        "display_name": "Максим",
        "username": "maks_seed",
        "age": 28,
        "gender": "Мужчина",
        "city": "Санкт-Петербург",
        "about": "Катаюсь на велосипеде, читаю нон-фикшн и иногда играю в настолки.",
        "want_gender": "Женщина",
        "want_age_min": 22,
        "want_age_max": 31,
        "want_city": "Не важно",
    },
    {
        "display_name": "Екатерина",
        "username": "katya_seed",
        "age": 26,
        "gender": "Женщина",
        "city": "Казань",
        "about": "Работаю в дизайне, люблю выставки и спонтанные поездки на выходные.",
        "want_gender": "Мужчина",
        "want_age_min": 25,
        "want_age_max": 35,
        "want_city": "Не важно",
    },
    {
        "display_name": "Илья",
        "username": "ilya_seed",
        "age": 30,
        "gender": "Мужчина",
        "city": "Новосибирск",
        "about": "Пишу код, бегаю по утрам и собираю плейлисты под разное настроение.",
        "want_gender": "Женщина",
        "want_age_min": 23,
        "want_age_max": 32,
        "want_city": "Не важно",
    },
    {
        "display_name": "Мария",
        "username": "maria_seed",
        "age": 27,
        "gender": "Женщина",
        "city": "Екатеринбург",
        "about": "Люблю йогу, кино на языке оригинала и разговоры до глубокой ночи.",
        "want_gender": "Мужчина",
        "want_age_min": 26,
        "want_age_max": 36,
        "want_city": "Не важно",
    },
    {
        "display_name": "Даниил",
        "username": "dan_seed",
        "age": 25,
        "gender": "Мужчина",
        "city": "Нижний Новгород",
        "about": "Фотографирую город, играю в теннис и люблю честные разговоры без масок.",
        "want_gender": "Женщина",
        "want_age_min": 21,
        "want_age_max": 29,
        "want_city": "Не важно",
    },
]


def api_request(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req) as response:
            body = response.read().decode("utf-8")
            if not body:
                return {}
            return json.loads(body)
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} -> {exc.code}: {details}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"{method} {url} failed: {exc.reason}") from exc


def build_profile(template: dict[str, Any], suffix: int) -> dict[str, Any]:
    profile = deepcopy(template)
    if suffix > 0:
        profile["display_name"] = f"{profile['display_name']} {suffix + 1}"
    profile["visible"] = True
    profile.pop("username", None)
    return profile


def seed_fake_users(
    count: int,
    start_id: int,
    user_service_url: str,
    anketa_service_url: str,
) -> list[int]:
    created_ids: list[int] = []

    for index in range(count):
        template = PROFILE_TEMPLATES[index % len(PROFILE_TEMPLATES)]
        user_id = start_id + index
        suffix = index // len(PROFILE_TEMPLATES)
        username = f"{template['username']}_{user_id}"
        profile = build_profile(template, suffix)

        api_request(
            "POST",
            f"{user_service_url.rstrip('/')}/users/",
            {"user_id": user_id, "username": username},
        )
        api_request(
            "PUT",
            f"{anketa_service_url.rstrip('/')}/anketas/{user_id}",
            profile,
        )
        created_ids.append(user_id)
        print(
            f"Created fake user {user_id}: {profile['display_name']}, "
            f"{profile['age']} лет, {profile['city']}"
        )

    return created_ids


def refresh_viewer_feed(recommendation_service_url: str, viewer_id: int) -> None:
    result = api_request(
        "POST",
        f"{recommendation_service_url.rstrip('/')}/recommendations/{viewer_id}/refresh",
    )
    print(
        f"Refreshed feed for {viewer_id}: cached_items={result.get('cached_items', 0)}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Создаёт искусственных пользователей и анкеты для локального теста бота."
    )
    parser.add_argument("--count", type=int, default=5, help="Сколько фейковых анкет создать.")
    parser.add_argument(
        "--start-id",
        type=int,
        default=900000001,
        help="С какого Telegram ID начинать генерацию.",
    )
    parser.add_argument(
        "--viewer-id",
        type=int,
        help="Telegram ID реального пользователя, для которого нужно обновить ленту.",
    )
    parser.add_argument(
        "--user-service-url",
        default="http://localhost:8000",
        help="URL user_service.",
    )
    parser.add_argument(
        "--anketa-service-url",
        default="http://localhost:8001",
        help="URL anketa_service.",
    )
    parser.add_argument(
        "--recommendation-service-url",
        default="http://localhost:8002",
        help="URL recommendation_service.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.count < 1:
        print("--count должен быть больше 0", file=sys.stderr)
        return 1

    try:
        created_ids = seed_fake_users(
            count=args.count,
            start_id=args.start_id,
            user_service_url=args.user_service_url,
            anketa_service_url=args.anketa_service_url,
        )
        if args.viewer_id is not None:
            refresh_viewer_feed(args.recommendation_service_url, args.viewer_id)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Done. Created {len(created_ids)} fake users.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
