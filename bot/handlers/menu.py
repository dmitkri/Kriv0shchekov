import html
import logging
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.fsm.states import AnketaStates
from bot.keyboards.inline import like_dislike_keyboard, profile_action_keyboard
from bot.keyboards.reply import (
    cancel_keyboard,
    city_preference_keyboard,
    gender_keyboard,
    main_menu_keyboard,
    preference_gender_keyboard,
)
from bot.services.anketa_api import AnketaAPIClient
from bot.services.recommendation_api import RecommendationAPIClient
from bot.services.user_api import UserAPIClient

logger = logging.getLogger(__name__)
router = Router()

GENDER_OPTIONS = {"Мужчина", "Женщина", "Другое"}
PREFERENCE_GENDER_OPTIONS = GENDER_OPTIONS | {"Не важно"}
ANY_CITY = "Не важно"


def _anketa_completed(anketa: dict[str, Any]) -> bool:
    completed = anketa.get("profile_completed")
    if isinstance(completed, bool):
        return completed
    required_fields = (
        "display_name",
        "age",
        "gender",
        "city",
        "about",
        "want_gender",
        "want_age_min",
        "want_age_max",
        "want_city",
    )
    return all(anketa.get(field) not in (None, "") for field in required_fields)


def _format_value(value: Any) -> str:
    if value in (None, ""):
        return "не указано"
    return html.escape(str(value))


def _prompt(label: str, current_value: Any = None) -> str:
    if current_value in (None, ""):
        return label
    return f"{label}\n\nСейчас: <b>{_format_value(current_value)}</b>"


def _format_anketa(anketa: dict[str, Any]) -> str:
    return (
        "<b>Твоя анкета</b>\n\n"
        f"<b>Имя:</b> {_format_value(anketa.get('display_name'))}\n"
        f"<b>Возраст:</b> {_format_value(anketa.get('age'))}\n"
        f"<b>Пол:</b> {_format_value(anketa.get('gender'))}\n"
        f"<b>Город:</b> {_format_value(anketa.get('city'))}\n"
        f"<b>О себе:</b> {_format_value(anketa.get('about'))}\n\n"
        "<b>Кого ищешь</b>\n"
        f"<b>Пол:</b> {_format_value(anketa.get('want_gender'))}\n"
        f"<b>Возраст:</b> {_format_value(anketa.get('want_age_min'))}"
        f" - {_format_value(anketa.get('want_age_max'))}\n"
        f"<b>Город:</b> {_format_value(anketa.get('want_city'))}"
    )


def _format_recommendation(profile: dict[str, Any]) -> str:
    scores = profile.get("scores", {})
    final_score = scores.get("final_score")
    compatibility = ""
    if isinstance(final_score, (int, float)):
        compatibility = f"\n\n<i>Совместимость: {final_score:.0%}</i>"

    return (
        f"<b>{_format_value(profile.get('display_name'))}, "
        f"{_format_value(profile.get('age'))}</b>\n"
        f"<b>Пол:</b> {_format_value(profile.get('gender'))}\n"
        f"<b>Город:</b> {_format_value(profile.get('city'))}\n\n"
        f"{_format_value(profile.get('about'))}"
        f"{compatibility}"
    )


async def _ensure_registered(
    message: Message | CallbackQuery,
    user_api: UserAPIClient,
    telegram_id: int,
) -> bool:
    user = await user_api.get_user(telegram_id)
    if user is not None:
        return True

    text = "Сначала зарегистрируйся через /start."
    if isinstance(message, CallbackQuery):
        await message.answer(text, show_alert=True)
    else:
        await message.answer(text)
    return False


async def _show_profile(
    message: Message,
    anketa_api: AnketaAPIClient,
) -> None:
    anketa = await anketa_api.get_anketa(message.from_user.id)
    if anketa and _anketa_completed(anketa):
        await message.answer(
            _format_anketa(anketa),
            reply_markup=profile_action_keyboard(profile_completed=True),
        )
        return

    await message.answer(
        "Анкета пока не заполнена. Нажми кнопку ниже, и мы соберём её по шагам.",
        reply_markup=profile_action_keyboard(profile_completed=False),
    )


async def _start_anketa_edit(
    message: Message,
    state: FSMContext,
    anketa: dict[str, Any] | None,
) -> None:
    anketa = anketa or {}
    await state.clear()
    await state.update_data(
        current_display_name=anketa.get("display_name"),
        current_age=anketa.get("age"),
        current_gender=anketa.get("gender"),
        current_city=anketa.get("city"),
        current_about=anketa.get("about"),
        current_want_gender=anketa.get("want_gender", "Не важно"),
        current_want_age_min=anketa.get("want_age_min", 18),
        current_want_age_max=anketa.get("want_age_max", 60),
        current_want_city=anketa.get("want_city", ANY_CITY),
    )
    await state.set_state(AnketaStates.waiting_for_name)
    await message.answer(
        _prompt("Как тебя зовут?", anketa.get("display_name")),
        reply_markup=cancel_keyboard(),
    )


async def _send_recommendation(message: Message, recommendation: dict[str, Any]) -> None:
    await message.answer(
        _format_recommendation(recommendation),
        reply_markup=like_dislike_keyboard(int(recommendation["account_id"])),
    )


@router.message(StateFilter(None), Command("myprofile"))
@router.message(StateFilter(None), F.text == "👤 Моя анкета")
async def my_profile(
    message: Message,
    user_api: UserAPIClient,
    anketa_api: AnketaAPIClient,
) -> None:
    if not await _ensure_registered(message, user_api, message.from_user.id):
        return
    await _show_profile(message, anketa_api)


@router.callback_query(F.data == "edit_profile")
async def edit_profile(
    callback: CallbackQuery,
    state: FSMContext,
    user_api: UserAPIClient,
    anketa_api: AnketaAPIClient,
) -> None:
    if not await _ensure_registered(callback, user_api, callback.from_user.id):
        return
    if callback.message is None:
        await callback.answer()
        return

    anketa = await anketa_api.get_anketa(callback.from_user.id)
    await callback.answer()
    await _start_anketa_edit(callback.message, state, anketa)


@router.message(StateFilter("*"), F.text == "Отмена")
async def cancel_anketa_edit(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Заполнение анкеты отменено.", reply_markup=main_menu_keyboard())


@router.message(AnketaStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2 or len(name) > 100:
        await message.answer(
            "Имя должно содержать от 2 до 100 символов.",
            reply_markup=cancel_keyboard(),
        )
        return

    await state.update_data(display_name=name)
    data = await state.get_data()
    await state.set_state(AnketaStates.waiting_for_age)
    await message.answer(
        _prompt("Сколько тебе лет?", data.get("current_age")),
        reply_markup=cancel_keyboard(),
    )


@router.message(AnketaStates.waiting_for_age)
async def process_age(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("Возраст нужно указать числом.", reply_markup=cancel_keyboard())
        return

    age = int(text)
    if age < 18 or age > 100:
        await message.answer(
            "Возраст должен быть в диапазоне от 18 до 100 лет.",
            reply_markup=cancel_keyboard(),
        )
        return

    await state.update_data(age=age)
    data = await state.get_data()
    await state.set_state(AnketaStates.waiting_for_gender)
    await message.answer(
        _prompt("Выбери свой пол.", data.get("current_gender")),
        reply_markup=gender_keyboard(),
    )


@router.message(AnketaStates.waiting_for_gender)
async def process_gender(message: Message, state: FSMContext) -> None:
    gender = (message.text or "").strip()
    if gender not in GENDER_OPTIONS:
        await message.answer(
            "Пожалуйста, выбери один из вариантов на клавиатуре ниже.",
            reply_markup=gender_keyboard(),
        )
        return

    await state.update_data(gender=gender)
    data = await state.get_data()
    await state.set_state(AnketaStates.waiting_for_city)
    await message.answer(
        _prompt("Из какого ты города?", data.get("current_city")),
        reply_markup=cancel_keyboard(),
    )


@router.message(AnketaStates.waiting_for_city)
async def process_city(message: Message, state: FSMContext) -> None:
    city = (message.text or "").strip()
    if len(city) < 2 or len(city) > 100:
        await message.answer(
            "Название города должно содержать от 2 до 100 символов.",
            reply_markup=cancel_keyboard(),
        )
        return

    await state.update_data(city=city)
    data = await state.get_data()
    await state.set_state(AnketaStates.waiting_for_about)
    await message.answer(
        _prompt(
            "Расскажи немного о себе. Достаточно 10-500 символов.",
            data.get("current_about"),
        ),
        reply_markup=cancel_keyboard(),
    )


@router.message(AnketaStates.waiting_for_about)
async def process_about(message: Message, state: FSMContext) -> None:
    about = (message.text or "").strip()
    if len(about) < 10 or len(about) > 500:
        await message.answer(
            "Описание должно содержать от 10 до 500 символов.",
            reply_markup=cancel_keyboard(),
        )
        return

    await state.update_data(about=about)
    data = await state.get_data()
    await state.set_state(AnketaStates.waiting_for_want_gender)
    await message.answer(
        _prompt("Кого ты ищешь по полу?", data.get("current_want_gender")),
        reply_markup=preference_gender_keyboard(),
    )


@router.message(AnketaStates.waiting_for_want_gender)
async def process_want_gender(message: Message, state: FSMContext) -> None:
    want_gender = (message.text or "").strip()
    if want_gender not in PREFERENCE_GENDER_OPTIONS:
        await message.answer(
            "Выбери один из вариантов на клавиатуре.",
            reply_markup=preference_gender_keyboard(),
        )
        return

    await state.update_data(want_gender=want_gender)
    data = await state.get_data()
    await state.set_state(AnketaStates.waiting_for_want_age_min)
    await message.answer(
        _prompt(
            "Укажи минимальный возраст, который тебе интересен.",
            data.get("current_want_age_min"),
        ),
        reply_markup=cancel_keyboard(),
    )


@router.message(AnketaStates.waiting_for_want_age_min)
async def process_want_age_min(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer(
            "Минимальный возраст нужно указать числом.",
            reply_markup=cancel_keyboard(),
        )
        return

    age_min = int(text)
    if age_min < 18 or age_min > 100:
        await message.answer(
            "Возраст должен быть в диапазоне от 18 до 100 лет.",
            reply_markup=cancel_keyboard(),
        )
        return

    await state.update_data(want_age_min=age_min)
    data = await state.get_data()
    await state.set_state(AnketaStates.waiting_for_want_age_max)
    await message.answer(
        _prompt(
            "Укажи максимальный возраст.",
            data.get("current_want_age_max"),
        ),
        reply_markup=cancel_keyboard(),
    )


@router.message(AnketaStates.waiting_for_want_age_max)
async def process_want_age_max(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer(
            "Максимальный возраст нужно указать числом.",
            reply_markup=cancel_keyboard(),
        )
        return

    age_max = int(text)
    data = await state.get_data()
    age_min = int(data["want_age_min"])

    if age_max < 18 or age_max > 100:
        await message.answer(
            "Возраст должен быть в диапазоне от 18 до 100 лет.",
            reply_markup=cancel_keyboard(),
        )
        return
    if age_max < age_min:
        await message.answer(
            "Максимальный возраст не может быть меньше минимального.",
            reply_markup=cancel_keyboard(),
        )
        return

    await state.update_data(want_age_max=age_max)
    data = await state.get_data()
    await state.set_state(AnketaStates.waiting_for_want_city)
    await message.answer(
        _prompt(
            "Есть предпочтение по городу? Можно выбрать Не важно.",
            data.get("current_want_city"),
        ),
        reply_markup=city_preference_keyboard(),
    )


@router.message(AnketaStates.waiting_for_want_city)
async def process_want_city(
    message: Message,
    state: FSMContext,
    anketa_api: AnketaAPIClient,
    recommendation_api: RecommendationAPIClient,
) -> None:
    want_city = (message.text or "").strip()
    if want_city != ANY_CITY and (len(want_city) < 2 or len(want_city) > 100):
        await message.answer(
            "Укажи город от 2 до 100 символов или выбери Не важно.",
            reply_markup=city_preference_keyboard(),
        )
        return

    data = await state.get_data()
    payload = {
        "display_name": data["display_name"],
        "age": data["age"],
        "gender": data["gender"],
        "city": data["city"],
        "about": data["about"],
        "want_gender": data["want_gender"],
        "want_age_min": data["want_age_min"],
        "want_age_max": data["want_age_max"],
        "want_city": want_city,
        "visible": True,
    }

    saved_anketa = await anketa_api.save_anketa(message.from_user.id, payload)
    if saved_anketa is None:
        logger.error("Failed to save anketa for user_id=%d", message.from_user.id)
        await message.answer(
            "Не получилось сохранить анкету. Попробуй ещё раз или нажми Отмена.",
            reply_markup=cancel_keyboard(),
        )
        return

    await recommendation_api.refresh_feed(message.from_user.id)
    await state.clear()
    await message.answer("✅ Анкета сохранена.", reply_markup=main_menu_keyboard())
    await message.answer(
        _format_anketa(saved_anketa),
        reply_markup=profile_action_keyboard(profile_completed=True),
    )


@router.message(StateFilter(None), Command("look"))
@router.message(StateFilter(None), F.text == "🔍 Смотреть анкеты")
async def browse_profiles(
    message: Message,
    user_api: UserAPIClient,
    anketa_api: AnketaAPIClient,
    recommendation_api: RecommendationAPIClient,
) -> None:
    if not await _ensure_registered(message, user_api, message.from_user.id):
        return

    anketa = await anketa_api.get_anketa(message.from_user.id)
    if anketa is None or not _anketa_completed(anketa):
        await message.answer(
            "Сначала заполни анкету в разделе 👤 Моя анкета, чтобы мы могли подобрать рекомендации."
        )
        return

    recommendation, error = await recommendation_api.get_next_recommendation(
        message.from_user.id
    )
    if recommendation is None:
        await message.answer(error or "Подходящих анкет пока нет.")
        return

    await _send_recommendation(message, recommendation)


async def _handle_reaction(
    callback: CallbackQuery,
    reaction_type: str,
    recommendation_api: RecommendationAPIClient,
) -> None:
    if callback.message is None:
        await callback.answer()
        return

    try:
        target_account_id = int((callback.data or "").split(":", 1)[1])
    except (IndexError, ValueError):
        await callback.answer("Не удалось обработать действие.", show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None)
    next_recommendation, error = await recommendation_api.submit_reaction(
        callback.from_user.id,
        target_account_id,
        reaction_type,
    )

    if error:
        await callback.answer(error, show_alert=True)
        return

    if reaction_type == "like":
        await callback.answer("Лайк сохранён")
    else:
        await callback.answer("Анкета пропущена")

    if next_recommendation is None:
        await callback.message.answer("Пока это все анкеты в твоей ленте.")
        return

    await _send_recommendation(callback.message, next_recommendation)


@router.callback_query(F.data.startswith("like:"))
async def like_profile(
    callback: CallbackQuery, recommendation_api: RecommendationAPIClient
) -> None:
    await _handle_reaction(callback, "like", recommendation_api)


@router.callback_query(F.data.startswith("skip:"))
async def skip_profile(
    callback: CallbackQuery, recommendation_api: RecommendationAPIClient
) -> None:
    await _handle_reaction(callback, "skip", recommendation_api)


@router.message(StateFilter(None), F.text == "❤️ Мэтчи")
async def my_matches(message: Message) -> None:
    await message.answer("Мэтчи будут следующим этапом. Пока доступны лайки и персональная лента.")


@router.message(StateFilter(None), F.text == "⚙️ Настройки")
async def settings(message: Message) -> None:
    await message.answer("Настройки — в разработке 🚧")
