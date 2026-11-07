from aiogram.fsm.state import State, StatesGroup


class DisputeStates(StatesGroup):
    reason = State()
    message = State()
    evidence = State()
