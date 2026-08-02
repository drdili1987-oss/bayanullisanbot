from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    choosing_language = State()
    entering_name = State()
    entering_phone = State()


class Homework(StatesGroup):
    choosing_lesson = State()
    waiting_content = State()


class QuizFlow(StatesGroup):
    choosing_level = State()
    answering = State()


class AdminReview(StatesGroup):
    waiting_grade = State()
    waiting_feedback = State()


class AdminBroadcast(StatesGroup):
    waiting_content = State()
    waiting_confirm = State()


class AdminLesson(StatesGroup):
    entering_title = State()       # Dars nomi
    entering_description = State() # Vazifa matni
    entering_media = State()       # Fayl/rasm (ixtiyoriy)
