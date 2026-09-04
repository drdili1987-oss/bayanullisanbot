from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    WebAppInfo,
)
from config import WEBHOOK_BASE_URL


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
    webapp_url = f"{WEBHOOK_BASE_URL.rstrip('/')}/app" if WEBHOOK_BASE_URL else ""
    btn_text = "🚀 Platformaga kirish (Web App)" if lang == "uz" else "🚀 Открыть платформу (Web App)"
    
    keyboard = []
    if webapp_url and webapp_url.startswith("https://"):
        keyboard.append([KeyboardButton(text=btn_text, web_app=WebAppInfo(url=webapp_url))])
    else:
        keyboard.append([KeyboardButton(text=btn_text)])

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
    for row in rows:
        keyboard.append([KeyboardButton(text=b) for b in row])
        
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
    keyboard = []
    webapp_url = f"{WEBHOOK_BASE_URL.rstrip('/')}/app" if WEBHOOK_BASE_URL else ""
    
    if webapp_url and webapp_url.startswith("https://"):
        keyboard.append([KeyboardButton(text="🚀 Platformaga kirish (Web App)", web_app=WebAppInfo(url=webapp_url))])
    else:
        keyboard.append([KeyboardButton(text="🚀 Platformaga kirish (Web App)")])

    rows = [
        ["📚 Kurslar", "👥 Foydalanuvchilar"],
        ["📝 Testlar", "📢 Broadcast"],
        ["🏆 Reyting"],
        ["👨‍🎓 Talaba rejimi"],
        ["🏠 Bosh menu"],
    ]
    for row in rows:
        keyboard.append([KeyboardButton(text=b) for b in row])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)



def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
