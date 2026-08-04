import os
import tempfile
import time

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services import firebase_service as fb
from states.states import Homework
from keyboards.reply import main_menu_kb
from utils.texts import t
from config import ADMIN_IDS

router = Router(name="courses_student")


@router.message(F.text.in_(["📚 Kurslar", "📚 Курсы"]))
async def start_courses(message: Message, state: FSMContext, db_user: dict | None):
    if not db_user:
        await message.answer(t("not_registered", "uz"))
        return

    lang = db_user.get("language", "uz")
    data = await state.get_data()
    category = data.get("current_section")

    if not category:
        await message.answer(
            "Bo'lim tanlanmagan. Iltimos, asosiy menyudan bo'limni tanlang." if lang == "uz"
            else "Раздел не выбран. Пожалуйста, выберите раздел из главного меню."
        )
        return

    courses = await fb.list_courses(category)
    
    builder = InlineKeyboardBuilder()
    for c in courses:
        title = f"{c.get('course_number', '?')}-kurs: {c.get('title', 'Nomsiz')}"
        builder.button(
            text=f"📖 {title}",
            callback_data=f"course_enter:{c['id']}"
        )
        
    test_text = "📝 Bo'lim bo'yicha test ishlash" if lang == "uz" else "📝 Пройти тест по разделу"
    builder.button(text=test_text, callback_data="start_quiz_flow")
    builder.adjust(1)

    if not courses:
        msg = f"'{category}' bo'limida hozircha kurslar yo'q, lekin test ishlashingiz mumkin." if lang == "uz" else f"В разделе '{category}' пока нет курсов, но вы можете пройти тест."
        await message.answer(msg, reply_markup=builder.as_markup())
    else:
        msg = "Qaysi kursni ko'rmoqchisiz?" if lang == "uz" else "Какой курс вы хотите посмотреть?"
        await message.answer(msg, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("course_enter:"))
async def course_enter(callback: CallbackQuery, state: FSMContext, db_user: dict | None):
    if not db_user:
        await callback.answer(t("not_registered", "uz"), show_alert=True)
        return

    course_id = callback.data.split(":", 1)[1]
    lang = db_user.get("language", "uz")
    allowed_courses = db_user.get("allowed_courses", [])
    
    course = await fb.get_course(course_id)
    if not course:
        await callback.answer("Kurs topilmadi.", show_alert=True)
        return

    # Check permission
    if course_id not in allowed_courses:
        # Request access from admin
        await callback.answer(
            "Sizda ushbu kursga ruxsat yo'q. Adminga so'rov yuborildi." if lang == "uz"
            else "У вас нет доступа к этому курсу. Запрос отправлен администратору.",
            show_alert=True
        )
        
        user_name = db_user.get("full_name", "Noma'lum")
        course_name = f"{course.get('course_number')}-kurs: {course.get('title')}"
        cat_name = course.get('category')
        
        # Admin notification
        builder = InlineKeyboardBuilder()
        builder.button(text=f"✅ Ruxsat berish", callback_data=f"grant_course:{db_user['telegram_id']}:{course_id}")
        
        admin_msg = f"🔔 <b>Ruxsat so'rovi!</b>\n\n👤 Talaba: {user_name}\n📂 Bo'lim: {cat_name}\n📚 Kurs: {course_name}"
        
        for admin_id in ADMIN_IDS:
            try:
                await callback.message.bot.send_message(
                    chat_id=admin_id,
                    text=admin_msg,
                    reply_markup=builder.as_markup()
                )
            except Exception:
                pass
        return

    # User has access, show course menu
    builder = InlineKeyboardBuilder()
    builder.button(text="📖 Qo'llanma", callback_data=f"course_manual:{course_id}")
    builder.button(text="📚 Darslar", callback_data=f"course_lessons:{course_id}")
    builder.adjust(1)
    
    title = f"{course.get('course_number')}-kurs: {course.get('title')}"
    msg = f"📚 <b>{title}</b>\n\nQuyidagilardan birini tanlang:" if lang == "uz" else f"📚 <b>{title}</b>\n\nВыберите один из вариантов:"
    
    await callback.message.edit_text(msg, reply_markup=builder.as_markup())


async def _send_media(bot, chat_id, media_type, media_url, text, protect_content=False):
    if not media_type or not media_url:
        await bot.send_message(chat_id, text, protect_content=protect_content)
        return
        
    caption = text if len(text) <= 1000 else ""
    if len(text) > 1000:
        await bot.send_message(chat_id, text, protect_content=protect_content)
        
    if media_type == "photo":
        await bot.send_photo(chat_id, media_url, caption=caption, protect_content=protect_content)
    elif media_type == "video":
        await bot.send_video(chat_id, media_url, caption=caption, protect_content=protect_content)
    elif media_type == "document":
        await bot.send_document(chat_id, media_url, caption=caption, protect_content=protect_content)
    elif media_type == "audio":
        await bot.send_audio(chat_id, media_url, caption=caption, protect_content=protect_content)
    elif media_type == "voice":
        await bot.send_voice(chat_id, media_url, caption=caption, protect_content=protect_content)
    elif media_type == "link":
        await bot.send_message(chat_id, f"{text}\n\nLink: {media_url}")
    else:
        await bot.send_message(chat_id, text)


@router.callback_query(F.data.startswith("course_manual:"))
async def course_manual(callback: CallbackQuery):
    course_id = callback.data.split(":", 1)[1]
    course = await fb.get_course(course_id)
    if not course:
        await callback.answer("Topilmadi.", show_alert=True)
        return
        
    text = course.get("manual_text", "")
    media_url = course.get("manual_media_url")
    media_type = course.get("manual_media_type")
    
    if not text and not media_url:
        await callback.answer("Hali kiritilmagan", show_alert=True)
        return
        
    await callback.answer()
    await _send_media(callback.message.bot, callback.from_user.id, media_type, media_url, text)


@router.callback_query(F.data.startswith("course_lessons:"))
async def course_lessons_list(callback: CallbackQuery):
    course_id = callback.data.split(":", 1)[1]
    lessons = await fb.get_course_lessons(course_id)
    
    builder = InlineKeyboardBuilder()
    if not lessons:
        await callback.answer("Hozircha darslar kiritilmagan", show_alert=True)
        return
        
    for lesson in lessons:
        lnum = lesson.get('lesson_number', '?')
        builder.button(text=f"{lnum}-dars", callback_data=f"clesson_view:{course_id}:{lnum}")
    
    builder.button(text="🔙 Orqaga", callback_data=f"course_enter:{course_id}")
    builder.adjust(2)
    
    await callback.message.edit_text("Kerakli darsni tanlang:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("clesson_view:"))
async def course_lesson_view(callback: CallbackQuery):
    _, course_id, lesson_num = callback.data.split(":")
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🎬 Video dars", callback_data=f"clesson_vid:{course_id}:{lesson_num}")
    builder.button(text="📝 Topshiriq", callback_data=f"clesson_hw_start:{course_id}:{lesson_num}")
    builder.button(text="🔙 Orqaga", callback_data=f"course_lessons:{course_id}")
    builder.adjust(2, 1)
    
    await callback.message.edit_text(f"<b>{lesson_num}-dars</b> menyusi:", reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("clesson_vid:"))
async def course_video(callback: CallbackQuery):
    _, course_id, lesson_num = callback.data.split(":")
    lesson = await fb.get_course_lesson(course_id, int(lesson_num))
    if not lesson:
        await callback.answer("Topilmadi.", show_alert=True)
        return
        
    text = lesson.get("video_text", "")
    media_url = lesson.get("video_media_url")
    media_type = lesson.get("video_media_type")
    
    if not text and not media_url:
        await callback.answer("Hali kiritilmagan", show_alert=True)
        return
        
    await callback.answer()
    await _send_media(callback.message.bot, callback.from_user.id, media_type, media_url, text, protect_content=True)


@router.callback_query(F.data.startswith("clesson_hw_start:"))
async def course_assignment(callback: CallbackQuery, state: FSMContext, db_user: dict | None):
    _, course_id, lesson_num = callback.data.split(":")
    lesson = await fb.get_course_lesson(course_id, int(lesson_num))
    if not lesson:
        await callback.answer("Topilmadi.", show_alert=True)
        return
        
    text = lesson.get("assignment_text", "")
    media_url = lesson.get("assignment_media_url")
    media_type = lesson.get("assignment_media_type")
    
    if not text and not media_url:
        await callback.answer("Hali kiritilmagan", show_alert=True)
        return
        
    lang = db_user.get("language", "uz") if db_user else "uz"
    
    await callback.answer()
    
    if text or media_url:
        await _send_media(callback.message.bot, callback.from_user.id, media_type, media_url, text, protect_content=True)
        
    # Render tests if any
    tests = lesson.get("tests", [])
    if tests:
        for idx, q in enumerate(tests):
            t_builder = InlineKeyboardBuilder()
            for opt_idx, opt in enumerate(q.get("options", [])):
                t_builder.button(text=opt, callback_data=f"lt:{course_id}:{lesson_num}:{idx}:{opt_idx}")
            t_builder.adjust(1)
            await callback.message.bot.send_message(
                callback.from_user.id,
                f"📝 <b>Test:</b> {q.get('question')}",
                reply_markup=t_builder.as_markup(),
                parse_mode="HTML"
            )
            
    builder = InlineKeyboardBuilder()
    builder.button(text="Javob jo'natish", callback_data=f"send_hw:{course_id}:{lesson_num}")
    await callback.message.bot.send_message(callback.from_user.id, "Javobingizni jo'natish uchun quyidagi tugmani bosing:", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("lt:"))
async def lesson_test_answer(callback: CallbackQuery):
    _, course_id, lesson_num, q_idx, opt_idx = callback.data.split(":")
    lesson = await fb.get_course_lesson(course_id, int(lesson_num))
    if not lesson:
        await callback.answer("Topilmadi.")
        return
        
    tests = lesson.get("tests", [])
    q_idx = int(q_idx)
    opt_idx = int(opt_idx)
    
    if q_idx >= len(tests):
        await callback.answer("Xato.", show_alert=True)
        return
        
    q = tests[q_idx]
    correct_idx = q.get("correct_option_index", 0)
    
    if opt_idx == correct_idx:
        result_text = "✅ To'g'ri"
        await callback.answer(f"{result_text}!", show_alert=True)
    else:
        result_text = "❌ Noto'g'ri"
        correct_text = q.get("options", [])[correct_idx] if correct_idx < len(q.get("options", [])) else "Noma'lum"
        await callback.answer(f"{result_text}!\nTo'g'ri javob: {correct_text}", show_alert=True)
        
    # Notify admins
    admins = [u for u in await fb.list_users() if u.get("role") == "admin"]
    course = await fb.get_course(course_id)
    course_name = course.get("title", f"{course_id}") if course else course_id
    user_name = callback.from_user.full_name
    
    admin_msg = (
        f"📊 <b>Test natijasi (Dars ichida)</b>\n\n"
        f"👤 Talaba: {user_name}\n"
        f"📚 Kurs: {course_name}\n"
        f"📖 Dars: {lesson_num}-dars\n"
        f"❓ Savol: {q.get('question')}\n"
        f"🎯 Natija: {result_text}"
    )
    for admin in admins:
        try:
            await callback.message.bot.send_message(admin["telegram_id"], admin_msg, parse_mode="HTML")
        except:
            pass

@router.callback_query(F.data.startswith("send_hw:"))
async def send_hw_start(callback: CallbackQuery, state: FSMContext):
    _, course_id, lesson_num = callback.data.split(":")
    await state.update_data(hw_course_id=course_id, hw_lesson_num=int(lesson_num))
    await state.set_state(Homework.waiting_content)
    
    await callback.message.answer("Javob matni, rasm, fayl yoki ovozli xabar jo'natishingiz mumkin:")
    await callback.answer()

@router.message(Homework.waiting_content)
async def process_homework(message: Message, state: FSMContext, db_user: dict | None):
    if not db_user:
        return
        
    data = await state.get_data()
    course_id = data.get("hw_course_id")
    lesson_num = data.get("hw_lesson_num")
    lang = db_user.get("language", "uz")

    if not course_id or not lesson_num:
        await message.answer("Xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.")
        await state.clear()
        return

    content_type = "text"
    content = message.text or ""
    file_id = None

    if message.photo:
        content_type = "photo"
        file_id = message.photo[-1].file_id
        content = message.caption or ""
    elif message.video:
        content_type = "video"
        file_id = message.video.file_id
        content = message.caption or ""
    elif message.audio:
        content_type = "audio"
        file_id = message.audio.file_id
        content = message.caption or ""
    elif message.document:
        content_type = "document"
        file_id = message.document.file_id
        content = message.caption or ""
    elif message.voice:
        content_type = "voice"
        file_id = message.voice.file_id
        content = ""

    hw_id = await fb.create_homework({
        "user_id": message.from_user.id,
        "course_id": course_id,
        "lesson_num": lesson_num,
        "content_type": content_type,
        "content": content,
        "file_id": file_id,
        "submitted_at": time.time(),
        "status": "pending"
    })

    await state.clear()
    await message.answer(t("homework_received", lang))

    # Adminga xabar
    course = await fb.get_course(course_id)
    c_title = f"{course.get('course_number')}-kurs" if course else course_id
    admin_msg = f"🔔 Yangi uy vazifasi!\n👤 Talaba: {db_user.get('full_name')}\n📚 Kurs: {c_title}\n📖 Dars: {lesson_num}"
    if content:
        admin_msg += f"\n\nJavob:\n{content}"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tekshirish va Baholash", callback_data=f"grade_hw:{hw_id}")
    reply_markup = builder.as_markup()
    
    for admin_id in ADMIN_IDS:
        try:
            if file_id:
                if content_type == "photo":
                    await message.bot.send_photo(admin_id, file_id, caption=admin_msg, reply_markup=reply_markup)
                elif content_type == "document":
                    await message.bot.send_document(admin_id, file_id, caption=admin_msg, reply_markup=reply_markup)
                elif content_type == "voice":
                    await message.bot.send_voice(admin_id, file_id, caption=admin_msg, reply_markup=reply_markup)
                elif content_type == "audio":
                    await message.bot.send_audio(admin_id, file_id, caption=admin_msg, reply_markup=reply_markup)
                elif content_type == "video":
                    await message.bot.send_video(admin_id, file_id, caption=admin_msg, reply_markup=reply_markup)
            else:
                await message.bot.send_message(admin_id, admin_msg, reply_markup=reply_markup)
        except:
            pass
