from aiogram import Router, F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup

from config import BRANCHES
from services.geo_service import sort_branches_by_distance
from utils.texts import t

router = Router(name="branches")


def _location_request_kb(lang: str) -> ReplyKeyboardMarkup:
    text = "📍 Joylashuvni yuborish" if lang == "uz" else "📍 Отправить геолокацию"
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text, request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


@router.message(F.text.in_(["📍 Filiallar", "📍 Филиалы"]))
async def show_branches(message: Message, db_user: dict | None):
    lang = db_user["language"] if db_user else "uz"
    lines = [t("branches", lang)]
    for b in BRANCHES:
        lines.append(f"• {b['name']}: https://maps.google.com/?q={b['lat']},{b['lon']}")
    await message.answer("\n".join(lines), reply_markup=_location_request_kb(lang))


@router.message(F.location)
async def branches_by_distance(message: Message, db_user: dict | None):
    lang = db_user["language"] if db_user else "uz"
    sorted_branches = sort_branches_by_distance(
        BRANCHES, message.location.latitude, message.location.longitude
    )
    lines = [t("branches", lang)]
    for b in sorted_branches:
        lines.append(f"• {b['name']} — {b['distance_km']} km")
    await message.answer("\n".join(lines))
