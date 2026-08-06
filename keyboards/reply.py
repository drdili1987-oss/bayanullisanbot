from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)


def language_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="O'zbekcha"), KeyboardButton(text="Русский")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def phone_kb(lang: str) -> ReplyKeyboardMarkup:
    text = "Telefon raqamni yuborish" if lang == "uz" else "Отправить номер телефона"
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text, request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_kb(lang: str, is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Talaba menyusi — adminga ko'rinmaydi."""
    if lang == "uz":
        rows = [
            ["📖 Sarf bo'limi", "📖 Nahv bo'limi"],
            ["📖 Balog'at bo'limi", "📖 She'riyat bo'limi"],
            ["📢 Telegram kanal"],
        ]
    else:
        rows = [
            ["📖 Раздел Сарф", "📖 Раздел Нахв"],
            ["📖 Раздел Балага", "📖 Раздел Поэзия"],
            ["📢 Telegram канал"],
        ]
    keyboard = [[KeyboardButton(text=b) for b in row] for row in rows]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def balogat_menu_kb(lang: str) -> ReplyKeyboardMarkup:
    if lang == "uz":
        rows = [["Maoniy bo'limi", "Bayon bo'limi"], ["Badiy bo'limi"], ["🔙 Orqaga"], ["🏠 Bosh menu"]]
    else:
        rows = [["Раздел Маани", "Раздел Баян"], ["Раздел Бади'"], ["🔙 Назад"], ["🏠 Главное меню"]]
    keyboard = [[KeyboardButton(text=b) for b in row] for row in rows]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def sher_sanati_menu_kb(lang: str) -> ReplyKeyboardMarkup:
    if lang == "uz":
        rows = [["Barmoq vazni", "Aruz"], ["Badiy san'atlar"], ["🔙 Orqaga"], ["🏠 Bosh menu"]]
    else:
        rows = [["Размер Бармак", "Аруз"], ["Поэтические искусства"], ["🔙 Назад"], ["🏠 Главное меню"]]
    keyboard = [[KeyboardButton(text=b) for b in row] for row in rows]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def section_action_kb(lang: str) -> ReplyKeyboardMarkup:
    if lang == "uz":
        rows = [["📚 Kurslar"], ["🔙 Orqaga"], ["🏠 Bosh menu"]]
    else:
        rows = [["📚 Курсы"], ["🔙 Назад"], ["🏠 Главное меню"]]
    keyboard = [[KeyboardButton(text=b) for b in row] for row in rows]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def admin_menu_kb() -> ReplyKeyboardMarkup:
    """Admin uchun alohida menyu."""
    rows = [
        ["📚 Kurslar", "👥 Foydalanuvchilar"],
        ["📝 Testlar", "📢 Broadcast"],
        ["🏆 Reyting"],
        ["👨‍🎓 Talaba rejimi"],
        ["🏠 Bosh menu"],
    ]
    keyboard = [[KeyboardButton(text=b) for b in row] for row in rows]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)



def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
