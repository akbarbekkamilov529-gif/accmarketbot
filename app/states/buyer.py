from aiogram.fsm.state import State, StatesGroup


class BuyerStates(StatesGroup):
    browse = State()
    view_account = State()
    purchase_warning = State()
    review_rating = State()
    review_comment = State()
