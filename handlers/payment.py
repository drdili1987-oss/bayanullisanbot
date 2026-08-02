from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import COURSE_PRICE
from services import firebase_service as fb
from services.payment_service import generate_click_link, generate_payme_link
from keyboards.inline import payment_provider_kb
from utils.texts import t

router = Router(name="payment")


@router.message(F.text.in_(["💳 To'lov", "💳 Оплата"]))
async def start_payment(message: Message, db_user: dict | None):
    if not db_user:
        await message.answer(t("not_registered", "uz"))
        return

    lang = db_user["language"]
    if db_user.get("has_access"):
        await message.answer(t("payment_success", lang))
        return

    await message.answer(
        t("pay_course", lang, price=COURSE_PRICE),
        reply_markup=payment_provider_kb(),
    )


@router.callback_query(F.data.startswith("pay:"))
async def choose_provider(callback: CallbackQuery, db_user: dict):
    provider = callback.data.split(":", 1)[1]

    payment_id = await fb.create_payment(
        {
            "user_id": callback.from_user.id,
            "amount": COURSE_PRICE,
            "provider": provider,
        }
    )

    if provider == "click":
        link = generate_click_link(payment_id, COURSE_PRICE)
    else:
        link = generate_payme_link(payment_id, COURSE_PRICE)

    builder = InlineKeyboardBuilder()
    builder.button(text="💳 To'lash", url=link)

    await callback.message.answer(
        f"To'lov havolasi tayyor (ID: {payment_id}):",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()
