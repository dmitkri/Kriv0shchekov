from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def like_dislike_keyboard(profile_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❤️ Лайк", callback_data=f"like:{profile_id}")
    builder.button(text="👎 Пропустить", callback_data=f"skip:{profile_id}")
    builder.adjust(2)
    return builder.as_markup()


def start_registration_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Зарегистрироваться", callback_data="start_registration")
    return builder.as_markup()


def profile_action_keyboard(profile_completed: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    button_text = "✏️ Редактировать анкету" if profile_completed else "📝 Заполнить анкету"
    builder.button(text=button_text, callback_data="edit_profile")
    return builder.as_markup()
