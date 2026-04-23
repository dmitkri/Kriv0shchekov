from aiogram.fsm.state import State, StatesGroup


class AnketaStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_gender = State()
    waiting_for_city = State()
    waiting_for_about = State()
    waiting_for_want_gender = State()
    waiting_for_want_age_min = State()
    waiting_for_want_age_max = State()
    waiting_for_want_city = State()
