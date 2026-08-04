from aiogram import Router

from . import (
    registration,
    courses_student,
    quiz,
    payment,
    branches,
    admin,
    admin_courses,
    admin_quizzes,
    navigation
)

def get_root_router() -> Router:
    root = Router()
    root.include_router(registration.router)
    root.include_router(navigation.router)
    root.include_router(admin.router)
    root.include_router(admin_courses.router)
    root.include_router(admin_quizzes.router)
    root.include_router(payment.router)       # payment OLDIN — pay_course_show/done callbacklari uchun
    root.include_router(courses_student.router)
    root.include_router(quiz.router)
    root.include_router(branches.router)
    return root
