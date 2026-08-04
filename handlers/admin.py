import asyncio

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services import firebase_service as fb
from states.states import AdminBroadcast, AdminReview
from keyboards.reply import admin_menu_kb, main_menu_kb
from keyboards.inline import admin_access_kb

router = Router(name="admin")


def _require_admin(db_user: dict | None) -> bool:
    return bool(db_user and db_user.get("role") == "admin")


@router.message(F.text == "👨‍🎓 Talaba rejimi")
async def switch_to_student(message: Message, db_user: dict | None):
    """Admin talaba rejimiga o'tadi."""
    if not _require_admin(db_user):
        return
    lang = db_user.get("language", "uz") if db_user else "uz"
    await message.answer("Talaba rejimi. Qaytish uchun /start bosing.", reply_markup=main_menu_kb(lang))





@router.message(F.text == "👥 Foydalanuvchilar")
async def admin_users_list(message: Message, db_user: dict | None):
    if not _require_admin(db_user):
        return
    users = await fb.list_users()
    students = [u for u in users if u.get("role") != "admin"]

    if not students:
        await message.answer("Hali hech qanday talaba yo'q.")
        return

    lines = [f"👥 <b>Jami talabalar: {len(students)} ta</b>\n"]
    for i, u in enumerate(students, 1):
        name = u.get("full_name") or u.get("name") or u.get("first_name") or "Nomsiz"
        username = u.get("username", "")
        uname_str = f" (@{username})" if username else ""
        phone = u.get("phone", "") or u.get("phone_number", "")
        phone_str = f" | 📞 {phone}" if phone else ""
        lines.append(f"{i}. 👤 <b>{name}</b>{uname_str}{phone_str}")

    text = "\n".join(lines)
    # Telegram 4096 belgi cheklov — bo'lib yuboramiz
    for start in range(0, len(text), 4000):
        await message.answer(text[start:start+4000], parse_mode="HTML")


@router.message(F.text == "🏆 Reyting")
async def admin_leaderboard(message: Message, db_user: dict | None):
    if not _require_admin(db_user):
        return

    leaderboard = await fb.get_leaderboard()

    if not leaderboard:
        await message.answer("Hali hech qanday ball yo'q.")
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 <b>Talabalar reytingi</b>\n"]
    for i, s in enumerate(leaderboard, 1):
        medal = medals[i - 1] if i <= 3 else f"{i}."
        name = s['name']
        total = s['total_score']
        hw = s['hw_score']
        hw_c = s['hw_count']
        qz = s['quiz_score']
        qz_q = s['quiz_questions']
        lines.append(
            f"{medal} <b>{name}</b> — <b>{total} ball</b>\n"
            f"   📝 Uy vazifasi: {hw} ball ({hw_c} ta)\n"
            f"   📊 Test: {qz}/{qz_q}"
        )

    text = "\n\n".join(lines)
    for start in range(0, len(text), 4000):
        await message.answer(text[start:start+4000], parse_mode="HTML")


@router.message(F.text == "📢 Broadcast")
async def admin_broadcast_menu(message: Message, state: FSMContext, db_user: dict | None):
    if not _require_admin(db_user):
        return
    await state.set_state(AdminBroadcast.waiting_content)
    await message.answer("Broadcast uchun xabar yuboring (matn/rasm/ovoz):")


@router.message(F.text == "🛠 Admin panel")
@router.message(Command("admin"))
async def admin_panel(message: Message, db_user: dict | None):
    if not _require_admin(db_user):
        return
    await message.answer("Admin paneli:", reply_markup=admin_menu_kb())


@router.callback_query(F.data.startswith("grade_hw:"))
async def admin_grade_hw_start(callback: CallbackQuery, state: FSMContext, db_user: dict | None):
    if not _require_admin(db_user):
        await callback.answer()
        return

    hw_id = callback.data.split(":", 1)[1]
    hw = await fb.get_homework(hw_id)
    if not hw:
        await callback.answer("Topshiriq topilmadi!")
        return

    if hw.get("status") == "graded":
        await callback.answer("Bu topshiriq allaqachon baholangan!", show_alert=True)
        return

    # Baholar klaviaturasi (1 dan 10 gacha)
    builder = InlineKeyboardBuilder()
    for i in range(1, 11):
        builder.button(text=str(i), callback_data=f"grade_val:{hw_id}:{i}")
    builder.adjust(5, 5)
    
    await callback.message.answer("Topshiriqqa necha baho qoyasiz (1-10)?", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("grade_val:"))
async def admin_grade_hw_val(callback: CallbackQuery, state: FSMContext, db_user: dict | None):
    if not _require_admin(db_user):
        await callback.answer()
        return

    _, hw_id, grade = callback.data.split(":")
    
    await state.update_data(grade_hw_id=hw_id, grade_val=grade)
    from states.states import AdminReview
    await state.set_state(AdminReview.waiting_feedback)
    
    await callback.message.edit_text(f"Baho: {grade}. Endi ushbu baho uchun izoh yozing:")
    await callback.answer()

@router.message(AdminReview.waiting_feedback, F.text | F.voice)
async def admin_grade_hw_feedback(message: Message, state: FSMContext, db_user: dict | None):
    if not _require_admin(db_user):
        return

    data = await state.get_data()
    hw_id = data.get("grade_hw_id")
    grade = data.get("grade_val")
    
    if message.voice:
        feedback = "Ovozli xabar 🎧"
        voice_id = message.voice.file_id
    else:
        feedback = message.text
        voice_id = None
    
    hw = await fb.get_homework(hw_id)
    if not hw:
        await state.clear()
        return
        
    await fb.update_homework(hw_id, {
        "status": "graded",
        "grade": grade,
        "comment": feedback,
        "voice_id": voice_id,
        "graded_at": __import__('time').time()
    })
    
    await state.clear()
    await message.answer("✅ Baho va izoh saqlandi, talabaga yuborildi.")
    
    # Notify student
    student_id = hw.get("user_id")
    if student_id:
        course_id = hw.get("course_id")
        lesson_num = hw.get("lesson_num", "?")
        course = await fb.get_course(course_id) if course_id else None
        c_title = f"{course.get('course_number')}-kurs" if course else "topshirig'ingiz"
        
        student_msg = f"🔔 <b>{c_title}, {lesson_num}-dars</b> bo'yicha javobingiz tekshirildi!\n\n⭐️ <b>Baho:</b> {grade}/10\n💬 <b>Ustoz izohi:</b> {feedback}"
        try:
            await message.bot.send_message(student_id, student_msg, parse_mode="HTML")
            if voice_id:
                await message.bot.send_voice(student_id, voice_id)
        except:
            pass


@router.callback_query(F.data == "admin:user_count")
async def admin_user_count(callback: CallbackQuery, db_user: dict | None):
    if not _require_admin(db_user):
        await callback.answer()
        return

    users = await fb.list_users()
    await callback.message.answer(f"Jami foydalanuvchilar: {len(users)}")
    await callback.answer()


@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext, db_user: dict | None):
    if not _require_admin(db_user):
        await callback.answer()
        return

    await state.set_state(AdminBroadcast.waiting_content)
    await callback.message.answer("Broadcast uchun xabar yuboring (matn/rasm/ovoz):")
    await callback.answer()


@router.message(AdminBroadcast.waiting_content)
async def admin_broadcast_preview(message: Message, state: FSMContext, db_user: dict | None):
    if not _require_admin(db_user):
        return

    await state.update_data(broadcast_message_id=message.message_id, broadcast_chat_id=message.chat.id)
    await state.set_state(AdminBroadcast.waiting_confirm)

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Yuborish", callback_data="broadcast:send")
    builder.button(text="❌ Bekor qilish", callback_data="broadcast:cancel")
    builder.adjust(2)
    await message.answer("Ushbu xabarni barcha foydalanuvchilarga yuborishni tasdiqlaysizmi?", reply_markup=builder.as_markup())


@router.callback_query(AdminBroadcast.waiting_confirm, F.data == "broadcast:cancel")
async def admin_broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Bekor qilindi.")
    await callback.answer()


@router.callback_query(AdminBroadcast.waiting_confirm, F.data == "broadcast:send")
async def admin_broadcast_send(callback: CallbackQuery, state: FSMContext, db_user: dict | None):
    if not _require_admin(db_user):
        await callback.answer()
        return

    data = await state.get_data()
    src_chat_id = data["broadcast_chat_id"]
    src_message_id = data["broadcast_message_id"]

    users = await fb.list_users()
    await state.clear()
    await callback.answer("Yuborilmoqda...")

    sent, failed = 0, 0
    for user in users:
        try:
            await callback.message.bot.copy_message(
                chat_id=user["telegram_id"],
                from_chat_id=src_chat_id,
                message_id=src_message_id,
            )
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    await callback.message.answer(f"Broadcast yakunlandi. Yuborildi: {sent}, xato: {failed}")


@router.callback_query(F.data.startswith("manage_access:"))
async def admin_manage_access(callback: CallbackQuery, db_user: dict | None):
    if not _require_admin(db_user):
        await callback.answer()
        return
    user_id = int(callback.data.split(":", 1)[1])
    target_user = await fb.get_user(user_id)
    if not target_user:
        await callback.answer("Foydalanuvchi topilmadi", show_alert=True)
        return
    allowed_sections = target_user.get("allowed_sections", [])
    await callback.message.edit_reply_markup(reply_markup=admin_access_kb(user_id, allowed_sections))
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_access:"))
async def admin_toggle_access(callback: CallbackQuery, db_user: dict | None):
    if not _require_admin(db_user):
        await callback.answer()
        return
    _, user_id_str, cat = callback.data.split(":", 2)
    user_id = int(user_id_str)
    
    target_user = await fb.get_user(user_id)
    if not target_user:
        await callback.answer("Foydalanuvchi topilmadi", show_alert=True)
        return
    
    allowed_sections = target_user.get("allowed_sections", [])
    if cat in allowed_sections:
        allowed_sections.remove(cat)
    else:
        allowed_sections.append(cat)
        
    await fb.update_user(user_id, {"allowed_sections": allowed_sections})
    
    await callback.message.edit_reply_markup(reply_markup=admin_access_kb(user_id, allowed_sections))
    await callback.answer()


@router.callback_query(F.data.startswith("save_access:"))
async def admin_save_access(callback: CallbackQuery, db_user: dict | None):
    if not _require_admin(db_user):
        await callback.answer()
        return
    user_id = int(callback.data.split(":", 1)[1])
    target_user = await fb.get_user(user_id)
    if not target_user:
        await callback.answer("Foydalanuvchi topilmadi", show_alert=True)
        return
        
    allowed_sections = target_user.get("allowed_sections", [])
    sections_text = "\n".join([f"✅ {s}" for s in allowed_sections]) if allowed_sections else "Hech qaysi bo'limga ruxsat berilmadi."
    
    msg = f"Sizga quyidagi bo'limlar bo'yicha uy vazifasini topshirishga ruxsat berildi:\n\n{sections_text}"
    
    try:
        await callback.message.bot.send_message(user_id, msg)
        await callback.answer("Foydalanuvchiga xabar yuborildi!", show_alert=True)
        await callback.message.delete()
    except Exception:
        await callback.answer("Foydalanuvchiga xabar yuborishda xatolik!", show_alert=True)

@router.callback_query(F.data.startswith("grant_course:"))
async def admin_grant_course(callback: CallbackQuery, db_user: dict | None):
    if not _require_admin(db_user):
        await callback.answer()
        return

    parts = callback.data.split(":", 2)
    target_user_id = int(parts[1])
    course_id = parts[2]

    target_user = await fb.get_user(target_user_id)
    if not target_user:
        await callback.answer("Foydalanuvchi topilmadi", show_alert=True)
        return

    course = await fb.get_course(course_id)
    if not course:
        await callback.answer("Kurs topilmadi", show_alert=True)
        return

    allowed_courses = target_user.get("allowed_courses", [])
    if course_id not in allowed_courses:
        allowed_courses.append(course_id)
        await fb.update_user(target_user_id, {"allowed_courses": allowed_courses})

    c_title = f"{course.get('course_number')}-kurs: {course.get('title')}"
    cat_name = course.get("category", "")

    # Notify student - kurs ochildi
    try:
        lang = target_user.get("language", "uz")
        msg = (
            f"🎉 <b>Tabriklaymiz!</b>\n\n"
            f"To'lovingiz tasdiqlandi va kurs ochildi!\n\n"
            f"📂 Bo'lim: {cat_name}\n"
            f"📚 Kurs: {c_title}\n\n"
            f"Endi kursga kirishingiz mumkin. 🚀"
        ) if lang == "uz" else (
            f"🎉 <b>Поздравляем!</b>\n\n"
            f"Ваш платёж подтверждён и курс открыт!\n\n"
            f"📂 Раздел: {cat_name}\n"
            f"📚 Курс: {c_title}\n\n"
            f"Теперь вы можете войти в курс. 🚀"
        )
        await callback.message.bot.send_message(target_user_id, msg, parse_mode="HTML")
    except Exception:
        pass

    await callback.message.edit_caption(
        caption=f"{callback.message.caption or ''}\n\n✅ <b>Ruxsat berildi va kurs ochildi!</b>",
        parse_mode="HTML",
        reply_markup=None
    )
    await callback.answer("✅ Ruxsat berildi!", show_alert=True)


@router.callback_query(F.data.startswith("reject_payment:"))
async def admin_reject_payment(callback: CallbackQuery, db_user: dict | None):
    if not _require_admin(db_user):
        await callback.answer()
        return

    parts = callback.data.split(":", 2)
    target_user_id = int(parts[1])
    course_id = parts[2]

    target_user = await fb.get_user(target_user_id)
    course = await fb.get_course(course_id)

    c_title = f"{course.get('course_number')}-kurs: {course.get('title')}" if course else course_id
    cat_name = course.get("category", "") if course else ""

    # Notify student - rad etildi
    try:
        lang = target_user.get("language", "uz") if target_user else "uz"
        msg = (
            f"❌ <b>To'lov tasdiqlanmadi</b>\n\n"
            f"📂 Bo'lim: {cat_name}\n"
            f"📚 Kurs: {c_title}\n\n"
            f"To'lovingiz admin tomonidan rad etildi.\n"
            f"Iltimos, qayta urinib ko'ring yoki admin bilan bog'laning."
        ) if lang == "uz" else (
            f"❌ <b>Платёж не подтверждён</b>\n\n"
            f"📂 Раздел: {cat_name}\n"
            f"📚 Курс: {c_title}\n\n"
            f"Ваш платёж отклонён администратором.\n"
            f"Пожалуйста, повторите попытку или обратитесь к администратору."
        )
        await callback.message.bot.send_message(target_user_id, msg, parse_mode="HTML")
    except Exception:
        pass

    await callback.message.edit_caption(
        caption=f"{callback.message.caption or ''}\n\n❌ <b>Rad etildi!</b>",
        parse_mode="HTML",
        reply_markup=None
    )
    await callback.answer("❌ Rad etildi!", show_alert=True)

