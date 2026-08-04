from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router(name="branches")

TELEGRAM_CHANNEL_URL = "https://t.me/Bayanul_lisan"


def telegram_channel_kb(lang: str) -> InlineKeyboardMarkup:
    text = "📢 Telegram kanalga o'tish" if lang == "uz" else "📢 Перейти в Telegram канал"
    builder = InlineKeyboardBuilder()
    builder.button(text=text, url=TELEGRAM_CHANNEL_URL)
    return builder.as_markup()


@router.message(F.text.in_(["📢 Telegram kanal", "📢 Telegram канал"]))
async def show_telegram_channel(message: Message, db_user: dict | None):
    lang = db_user["language"] if db_user else "uz"

    msg = (
        "📢 <b>Bayanul Lisan rasmiy Telegram kanali</b>\n\n"
        "Kanalimizda eng so'nggi yangiliklar, darslar va foydali materiallar joylashtiriladi.\n\n"
        "👇 Quyidagi tugmani bosib kanalga qo'shiling:"
    ) if lang == "uz" else (
        "📢 <b>Официальный Telegram канал Bayanul Lisan</b>\n\n"
        "На нашем канале публикуются последние новости, уроки и полезные материалы.\n\n"
        "👇 Нажмите кнопку ниже, чтобы присоединиться к каналу:"
    )

    await message.answer(msg, reply_markup=telegram_channel_kb(lang), parse_mode="HTML")
