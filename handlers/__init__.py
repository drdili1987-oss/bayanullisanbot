from aiogram import Router

from . import registration, homework, quiz, payment, branches, admin, admin_lessons


def get_root_router() -> Router:
    root = Router()
    root.include_router(registration.router)
    root.include_router(admin.router)
    root.include_router(admin_lessons.router)
    root.include_router(homework.router)
    root.include_router(quiz.router)
    root.include_router(payment.router)
    root.include_router(branches.router)
    return root
