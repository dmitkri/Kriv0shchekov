from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Моя анкета"), KeyboardButton(text="🔍 Смотреть анкеты")],
            [KeyboardButton(text="❤️ Мэтчи"), KeyboardButton(text="⚙️ Настройки")],
        ],
        resize_keyboard=True,
    )


def gender_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Мужчина"), KeyboardButton(text="Женщина")],
            [KeyboardButton(text="Другое")],
            [KeyboardButton(text="Отмена")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def preference_gender_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Мужчина"), KeyboardButton(text="Женщина")],
            [KeyboardButton(text="Другое"), KeyboardButton(text="Не важно")],
            [KeyboardButton(text="Отмена")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def city_preference_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Не важно")],
            [KeyboardButton(text="Отмена")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


remove_keyboard = ReplyKeyboardRemove()
