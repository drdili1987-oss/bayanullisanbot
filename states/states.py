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


class AdminCourse(StatesGroup):
    choosing_category = State()
    entering_number = State()
    entering_title = State()
    
class AdminCourseEdit(StatesGroup):
    waiting_course_number = State()
    
    # Qo'llanma
    waiting_manual_text = State()
    waiting_manual_media = State()
    
    # Video
    waiting_lesson_num_for_video = State()
    waiting_video_text = State()
    waiting_video_media = State()
    
    # Topshiriq
    waiting_lesson_num_for_assignment = State()
    waiting_assignment_text = State()
    waiting_assignment_media = State()
    
    # Dars ichidagi test
    waiting_test_question = State()
    waiting_test_options = State()
    waiting_test_correct_answer = State()

class AdminQuiz(StatesGroup):
    choosing_category = State()
    choosing_level = State()
    entering_question = State()
    entering_options = State()
    entering_correct = State()


class PaymentFlow(StatesGroup):
    waiting_screenshot = State()
