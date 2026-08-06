from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

LESSONS = [f"Dars {i}" for i in range(1, 11)]
LEVELS = ["beginner", "intermediate", "advanced"]


def lessons_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i, lesson in enumerate(LESSONS, start=1):
        builder.button(text=lesson, callback_data=f"lesson:{i}")
    builder.adjust(2)
    return builder.as_markup()


def levels_kb(lang: str) -> InlineKeyboardMarkup:
    labels = {
        "beginner": "Boshlang'ich" if lang == "uz" else "Начальный",
        "intermediate": "O'rta" if lang == "uz" else "Средний",
        "advanced": "Yuqori" if lang == "uz" else "Продвинутый",
    }
    builder = InlineKeyboardBuilder()
    for level in LEVELS:
        builder.button(text=labels[level], callback_data=f"level:{level}")
    builder.adjust(1)
    return builder.as_markup()


def quiz_options_kb(quiz_id: str, options: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for idx, option in enumerate(options):
        builder.button(text=option, callback_data=f"answer:{quiz_id}:{idx}")
    builder.adjust(1)
    return builder.as_markup()


def payment_provider_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Click", callback_data="pay:click")
    builder.button(text="Payme", callback_data="pay:payme")
    builder.adjust(2)
    return builder.as_markup()


def homework_review_kb(hw_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Baholash", callback_data=f"hw_grade:{hw_id}")
    builder.button(text="❌ Rad etish", callback_data=f"hw_reject:{hw_id}")
    builder.adjust(2)
    return builder.as_markup()


def grade_kb(hw_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for grade in range(1, 6):
        builder.button(text=str(grade), callback_data=f"hw_set_grade:{hw_id}:{grade}")
    builder.adjust(5)
    return builder.as_markup()


def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Yuborish", callback_data="broadcast:send")
    builder.button(text="❌ Bekor qilish", callback_data="broadcast:cancel")
    builder.adjust(2)
    return builder.as_markup()

def admin_category_kb() -> InlineKeyboardMarkup:
    categories = [
        "Sarf", "Nahv",
        "Balog'at - Maoniy", "Balog'at - Bayon", "Balog'at - Badiy",
        "She'riyat"
    ]
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat, callback_data=f"cat:{cat}")
    builder.adjust(2)
    return builder.as_markup()


def admin_new_user_kb(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⚙️ Ruxsatlarni boshqarish", callback_data=f"manage_access:{user_id}")
    return builder.as_markup()


def admin_access_kb(user_id: int, allowed_sections: list[str]) -> InlineKeyboardMarkup:
    categories = [
        "Sarf", "Nahv",
        "Balog'at - Maoniy", "Balog'at - Bayon", "Balog'at - Badiy",
        "She'riyat"
    ]
    builder = InlineKeyboardBuilder()
    for cat in categories:
        mark = "✅" if cat in allowed_sections else "❌"
        builder.button(text=f"{mark} {cat}", callback_data=f"toggle_access:{user_id}:{cat}")
    
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="✅ Tasdiqlash va Xabar yuborish", callback_data=f"save_access:{user_id}"))
    return builder.as_markup()


def student_manage_kb(user_id: int) -> InlineKeyboardMarkup:
    """Talabani boshqarish tugmalari."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⚙️ Ruxsatlarni boshqarish", callback_data=f"manage_access:{user_id}")
    builder.button(text="🗑 Talabani o'chirish", callback_data=f"student_delete_ask:{user_id}")
    builder.adjust(1)
    return builder.as_markup()


def student_delete_confirm_kb(user_id: int) -> InlineKeyboardMarkup:
    """O'chirishni tasdiqlash."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, o'chirish", callback_data=f"student_delete_confirm:{user_id}")
    builder.button(text="❌ Yo'q, bekor", callback_data=f"student_delete_cancel:{user_id}")
    builder.adjust(2)
    return builder.as_markup()
