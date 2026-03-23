# TinderBot — Dating бот в Telegram

Телеграм-бот для знакомств. Пользователи создают анкету, смотрят анкеты других, ставят лайки и получают мэтчи.

---

## Архитектура

Проект построен на микросервисах. Каждый сервис отвечает за свою область и общается с остальными через HTTP или Redis Streams.

```
[ Пользователь ]
      |
[ Telegram API ]
      |
  [ Bot Service ]  ←──────────────────────────┐
   /    |    \                                 |
  /     |     \                          Redis Streams
 ↓      ↓      ↓                         (события)
[User] [Profile] [Ranking]                    |
Service  Service   Service              [ Reaction Service ]
  \       |          |
   \      |        Redis
    \     |       (кэш × 10)
     ↓    ↓
   [ PostgreSQL ]

                    [ Storage Service ]
                           |
                        [ MinIO ]
```

---

## Сервисы

**Bot Service** — aiogram 3.x

Обрабатывает всё взаимодействие с пользователем в Telegram. FSM-машина состояний ведёт пользователя по шагам при заполнении анкеты. Показывает чужие анкеты, принимает реакции, шлёт уведомления о мэтчах. Слушает события из Redis Streams.

Команды: `/start`, `/edit`, `/browse`, `/matches`

---

**User Service** — FastAPI

Регистрирует пользователя при первом `/start` по его `telegram_id`. Хранит базовую информацию: id, username, статус активности. Остальные сервисы обращаются сюда для проверки существования пользователя.

---

**Profile Service** — FastAPI

Хранит анкеты. Поля: имя, возраст, пол, город, описание, интересы, предпочтения партнёра. При обновлении анкеты публикует событие в Redis Streams — Ranking Service пересчитает первичный рейтинг.

---

**Ranking Service** — FastAPI + Redis

Ранжирует анкеты по трём уровням (анкета → поведение → комбо). При старте сессии просчитывает первую анкету полностью, следующие 10 кладёт в Redis. Пользователь получает их мгновенно. На последней — цикл повторяется.

---

**Reaction Service** — FastAPI

Принимает лайки и пропуски. При лайке проверяет: а вдруг тот человек тоже лайкнул? Если да — создаёт мэтч и бросает событие `match.new` в Redis Streams.

---

**Storage Service** — FastAPI + MinIO

Принимает фото, кладёт в MinIO (S3-хранилище), отдаёт ключ. В базе хранится только ключ, сам файл живёт в MinIO. Максимум 5 фото на профиль.

---

## Схема базы данных

```
┌──────────────┐         ┌──────────────────────────────┐
│    users     │         │          profiles            │
├──────────────┤         ├──────────────────────────────┤
│ id (PK)      │──1:1───►│ id (PK)                      │
│ telegram_id  │         │ user_id (FK → users)         │
│ username     │         │ name, age, gender, city, bio │
│ is_active    │         │ interests (TEXT[])           │
│ created_at   │         │ pref_age_min, pref_age_max   │
└──────────────┘         │ pref_gender, pref_city       │
                         │ photos_count, is_visible     │
                         └──────────┬───────────────────┘
                                    │
                    ┌───────────────┼───────────────────┐
                    │               │                   │
                    ▼               ▼                   ▼
           ┌──────────────┐ ┌─────────────┐   ┌──────────────┐
           │    photos    │ │   ratings   │   │  reactions   │
           ├──────────────┤ ├─────────────┤   ├──────────────┤
           │ id (PK)      │ │ profile_id  │   │ id (PK)      │
           │ profile_id   │ │ primary_    │   │ from_user_id │
           │ s3_key       │ │  score      │   │ to_profile_id│
           │ order_num    │ │ behavior_   │   │ type         │
           └──────────────┘ │  score      │   │ (like/skip)  │
                            │ combined_   │   └──────────────┘
                            │  score      │
                            │ recalc_at   │
                            └─────────────┘

           ┌──────────────────────────────┐
           │           matches            │
           ├──────────────────────────────┤
           │ id (PK)                      │
           │ user1_id (FK → users)        │
           │ user2_id (FK → users)        │
           │ is_active, created_at        │
           └──────────────────────────────┘
```

### SQL

```sql
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE NOT NULL,
    username    VARCHAR(64),
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE profiles (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name         VARCHAR(100) NOT NULL,
    age          SMALLINT NOT NULL CHECK (age BETWEEN 18 AND 100),
    gender       VARCHAR(10) NOT NULL,
    city         VARCHAR(100),
    bio          TEXT,
    interests    TEXT[],
    pref_age_min SMALLINT DEFAULT 18,
    pref_age_max SMALLINT DEFAULT 60,
    pref_gender  VARCHAR(10),
    pref_city    VARCHAR(100),
    photos_count SMALLINT DEFAULT 0,
    is_visible   BOOLEAN DEFAULT TRUE,
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE photos (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    s3_key     VARCHAR(255) NOT NULL,
    order_num  SMALLINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ratings (
    profile_id      UUID PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
    primary_score   FLOAT DEFAULT 0.0,
    behavior_score  FLOAT DEFAULT 0.0,
    combined_score  FLOAT DEFAULT 0.0,
    likes_count     INTEGER DEFAULT 0,
    skips_count     INTEGER DEFAULT 0,
    recalculated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE reactions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_user_id  UUID NOT NULL REFERENCES users(id),
    to_profile_id UUID NOT NULL REFERENCES profiles(id),
    reaction_type VARCHAR(10) NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(from_user_id, to_profile_id)
);

CREATE TABLE matches (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user1_id   UUID NOT NULL REFERENCES users(id),
    user2_id   UUID NOT NULL REFERENCES users(id),
    is_active  BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user1_id, user2_id)
);
```

---

## Стек

| | |
|---|---|
| Бот | aiogram 3.x |
| API | FastAPI |
| БД | PostgreSQL 16 |
| Кэш / события | Redis 7 + Redis Streams |
| Фоновые задачи | Celery + Celery Beat |
| Хранилище фото | MinIO (S3) |
| Контейнеры | Docker Compose |
