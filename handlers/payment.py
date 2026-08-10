import time

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import CARD_NUMBER, CARD_OWNER, COURSE_PRICE, ADMIN_IDS
from services import firebase_service as fb
from states.states import PaymentFlow
from utils.texts import t

router = Router(name="payment")


@router.callback_query(F.data.startswith("pay_course_show:"))
async def pay_course_show_card(callback: CallbackQuery, db_user: dict | None):
    """Karta raqami va egasini ko'rsatish"""
    if not db_user:
        await callback.answer(t("not_registered", "uz"), show_alert=True)
        return

    course_id = callback.data.split(":", 1)[1]
    lang = db_user.get("language", "uz")

    course = await fb.get_course(course_id)
    course_num = course.get("course_number", "?") if course else "?"
    course_title = course.get("title") or course.get("name") or "Nomsiz"
    cat_name = course.get("category") or "Noma'lum"

    default_price = 120000 if cat_name == "She'riyat" else COURSE_PRICE
    price = course.get("price", default_price) if course else default_price

    card_text = (
        f"💳 <b>To'lov ma'lumotlari</b>\n\n"
        f"📚 Kurs: {course_num}-kurs — {course_title}\n"
        f"💰 Narxi: <b>{price:,} so'm</b>\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"🏦 Karta raqami:\n"
        f"<code>{CARD_NUMBER}</code>\n\n"
        f"👤 Karta egasi:\n"
        f"<b>{CARD_OWNER}</b>\n"
        f"━━━━━━━━━━━━━━━━━\n\n"
        f"⚠️ To'lovni amalga oshirgach, <b>«✅ To'lov qildim»</b> tugmasini bosing."
    ) if lang == "uz" else (
        f"💳 <b>Данные для оплаты</b>\n\n"
        f"📚 Курс: {course_num}-курс — {course_title}\n"
        f"💰 Стоимость: <b>{price:,} сум</b>\n\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"🏦 Номер карты:\n"
        f"<code>{CARD_NUMBER}</code>\n\n"
        f"👤 Владелец карты:\n"
        f"<b>{CARD_OWNER}</b>\n"
        f"━━━━━━━━━━━━━━━━━\n\n"
        f"⚠️ После оплаты нажмите кнопку <b>«✅ Я оплатил»</b>."
    )

    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ To'lov qildim" if lang == "uz" else "✅ Я оплатил",
        callback_data=f"pay_course_done:{course_id}"
    )
    builder.button(
        text="🔙 Orqaga" if lang == "uz" else "🔙 Назад",
        callback_data=f"course_enter:{course_id}"
    )
    builder.adjust(1)

    await callback.message.edit_text(card_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("pay_course_done:"))
async def pay_course_done(callback: CallbackQuery, state: FSMContext, db_user: dict | None):
    """Talaba to'lov qildim tugmasini bosdi - screenshot so'rash"""
    if not db_user:
        await callback.answer(t("not_registered", "uz"), show_alert=True)
        return

    course_id = callback.data.split(":", 1)[1]
    lang = db_user.get("language", "uz")

    course = await fb.get_course(course_id)
    if not course:
        await callback.answer(
            "⚠️ Kurs topilmadi. U o'chirilgan bo'lishi mumkin." if lang == "uz" else "⚠️ Курс не найден. Возможно, он был удален.", 
            show_alert=True
        )
        return

    await state.update_data(paying_course_id=course_id)
    await state.set_state(PaymentFlow.waiting_screenshot)

    screenshot_msg = (
        "📸 <b>Screenshot yuborish</b>\n\n"
        "To'lov amalga oshirilganligini tasdiqlash uchun\n"
        "to'lov screenshotini shu yerga yuboring.\n\n"
        "Admin ko'rib chiqgach, kurs ochiladi. ⏳"
    ) if lang == "uz" else (
        "📸 <b>Отправьте скриншот</b>\n\n"
        "Для подтверждения оплаты отправьте\n"
        "скриншот чека в этот чат.\n\n"
        "После проверки администратором курс будет открыт. ⏳"
    )

    await callback.message.answer(screenshot_msg, parse_mode="HTML")
    await callback.answer()


@router.message(PaymentFlow.waiting_screenshot, F.photo)
async def receive_payment_screenshot(message: Message, state: FSMContext, db_user: dict | None):
    """Screenshot qabul qilish va adminga yuborish"""
    if not db_user:
        return

    data = await state.get_data()
    course_id = data.get("paying_course_id")
    lang = db_user.get("language", "uz")

    if not course_id:
        await message.answer("Xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.")
        await state.clear()
        return

    await state.clear()

    course = await fb.get_course(course_id)
    if not course:
        msg = "⚠️ Kurs topilmadi. U o'chirilgan bo'lishi mumkin." if lang == "uz" else "⚠️ Курс не найден. Возможно, он был удален."
        await message.answer(msg)
        return

    course_num = course.get("course_number", "?")
    course_title = course.get("title") or course.get("name") or "Nomsiz"
    cat_name = course.get("category") or "Noma'lum"

    user_name = db_user.get("full_name") or db_user.get("name") or message.from_user.full_name
    user_id = message.from_user.id

    # Talabaga tasdiqlash xabari
    confirm_msg = (
        "✅ <b>Screenshot qabul qilindi!</b>\n\n"
        "Admin to'lovingizni tekshirib, ruxsat beradi.\n"
        "Biroz kuting... ⏳"
    ) if lang == "uz" else (
        "✅ <b>Скриншот получен!</b>\n\n"
        "Администратор проверит оплату и откроет доступ.\n"
        "Подождите немного... ⏳"
    )
    await message.answer(confirm_msg, parse_mode="HTML")

    # Adminlarga xabar yuborish
    screenshot_file_id = message.photo[-1].file_id

    admin_msg = (
        f"💰 <b>To'lov so'rovi!</b>\n\n"
        f"👤 Talaba: {user_name}\n"
        f"🆔 Telegram ID: {user_id}\n"
        f"📂 Bo'lim: {cat_name}\n"
        f"📚 Kurs: {course_num}-kurs — {course_title}\n"
        f"🔑 Kurs ID: <code>{course_id}</code>\n\n"
        f"📸 To'lov screenshoti yuborildi."
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Ruxsat berish va Kursni ochish",
        callback_data=f"grant_course:{user_id}:{course_id}"
    )
    builder.button(
        text="❌ Rad etish",
        callback_data=f"reject_payment:{user_id}:{course_id}"
    )
    builder.adjust(1)

    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_photo(
                chat_id=admin_id,
                photo=screenshot_file_id,
                caption=admin_msg,
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
        except Exception:
            pass


@router.message(PaymentFlow.waiting_screenshot)
async def receive_payment_screenshot_wrong(message: Message, db_user: dict | None):
    """Noto'g'ri format - faqat rasm kutilmoqda"""
    lang = db_user.get("language", "uz") if db_user else "uz"
    msg = (
        "⚠️ Iltimos, faqat <b>rasm (screenshot)</b> yuboring.\n"
        "To'lov screenshotini rasm ko'rinishida yuboring."
    ) if lang == "uz" else (
        "⚠️ Пожалуйста, отправьте только <b>изображение (скриншот)</b>.\n"
        "Скриншот оплаты должен быть в виде фото."
    )
    await message.answer(msg, parse_mode="HTML")
