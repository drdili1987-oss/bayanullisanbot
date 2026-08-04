import os
import tempfile

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services import firebase_service as fb
from states.states import AdminCourse, AdminCourseEdit
from keyboards.reply import admin_menu_kb
from keyboards.inline import admin_category_kb

router = Router(name="admin_courses")

def _require_admin(db_user: dict | None) -> bool:
    return bool(db_user and db_user.get("role") == "admin")

def _courses_list_kb(courses: list[dict]):
    builder = InlineKeyboardBuilder()
    for c in courses:
        title = f"{c.get('course_number', '?')}-kurs: {c.get('title', 'Nomsiz')}"
        builder.button(text=f"📖 {title}", callback_data=f"course_view:{c['id']}")
    builder.button(text="➕ Yangi kurs qo'shish", callback_data="course_add")
    builder.adjust(1)
    return builder.as_markup()

def _course_manage_kb(course_id: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="📖 Qo'llanma", callback_data=f"cedit_manual:{course_id}")
    builder.button(text="🎬 Video dars", callback_data=f"cedit_video:{course_id}")
    builder.button(text="📝 Topshiriq", callback_data=f"cedit_assignment:{course_id}")
    builder.button(text="🗑 O'chirish", callback_data=f"course_del:{course_id}")
    builder.button(text="🔙 Orqaga", callback_data="course_back")
    builder.adjust(2, 1, 2)
    return builder.as_markup()

def _skip_media_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="⏩ Mediasiz saqlash", callback_data="cedit_skip_media")
    return builder.as_markup()


@router.message(F.text == "📚 Kurslar", lambda msg, db_user: _require_admin(db_user))
async def admin_courses_menu(message: Message, db_user: dict | None):
    courses = await fb.list_courses()
    text = f"Jami {len(courses)} ta kurs mavjud:" if courses else "Hozircha hech qanday kurs yo'q."
    await message.answer(text, reply_markup=_courses_list_kb(courses))

@router.callback_query(F.data == "course_back")
async def course_back(callback: CallbackQuery, db_user: dict | None):
    if not _require_admin(db_user):
        await callback.answer()
        return
    courses = await fb.list_courses()
    await callback.message.edit_text(f"Jami {len(courses)} ta kurs mavjud:", reply_markup=_courses_list_kb(courses))
    await callback.answer()

@router.callback_query(F.data.startswith("course_view:"))
async def course_view(callback: CallbackQuery, db_user: dict | None, course_id: str = None):
    if not _require_admin(db_user):
        await callback.answer()
        return
    course_id = course_id or callback.data.split(":", 1)[1]
    course = await fb.get_course(course_id)
    if not course:
        await callback.answer("Topilmadi.")
        return

    text = (
        f"📚 <b>{course.get('course_number')}-kurs: {course.get('title')}</b>\n"
        f"📂 Bo'lim: {course.get('category')}\n\n"
        f"Quyidagilarni tahrirlashingiz mumkin:"
    )
    await callback.message.edit_text(text, reply_markup=_course_manage_kb(course_id))
    await callback.answer()


@router.callback_query(F.data.startswith("course_del:"))
async def course_delete(callback: CallbackQuery, db_user: dict | None):
    if not _require_admin(db_user):
        await callback.answer()
        return
    course_id = callback.data.split(":", 1)[1]
    await fb.delete_course(course_id)

    courses = await fb.list_courses()
    text = f"O'chirildi. Jami {len(courses)} ta kurs qoldi:" if courses else "Barcha kurslar o'chirildi."
    await callback.message.edit_text(text, reply_markup=_courses_list_kb(courses))
    await callback.answer("O'chirildi!")


@router.callback_query(F.data == "course_add")
async def course_add_start(callback: CallbackQuery, state: FSMContext, db_user: dict | None):
    if not _require_admin(db_user):
        await callback.answer()
        return
    await state.set_state(AdminCourse.choosing_category)
    await callback.message.answer("1-qadam: Kurs qaysi bo'limga tegishli?", reply_markup=admin_category_kb())
    await callback.answer()

@router.callback_query(AdminCourse.choosing_category, F.data.startswith("cat:"))
async def course_choose_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":", 1)[1]
    await state.update_data(category=category)
    await state.set_state(AdminCourse.entering_number)
    await callback.message.answer(f"Bo'lim: <b>{category}</b>\n2-qadam: Kurs raqamini kiriting (masalan: 1, 2, 3):")
    await callback.answer()

@router.message(AdminCourse.entering_number, F.text)
async def course_enter_number(message: Message, state: FSMContext):
    await state.update_data(course_number=message.text.strip())
    await state.set_state(AdminCourse.entering_title)
    await message.answer("3-qadam: Kurs nomini kiriting (masalan: Mubtado va Xabar):")

@router.message(AdminCourse.entering_title, F.text)
async def course_enter_title(message: Message, state: FSMContext):
    data = await state.get_data()
    course_id = await fb.create_course({
        "category": data["category"],
        "course_number": data["course_number"],
        "title": message.text.strip()
    })
    await state.clear()
    
    await message.answer(f"✅ Kurs yaratildi!\nEndi kurs ichiga kirib Qo'llanma, Video va Topshiriqlarni yuklashingiz mumkin.")
    
    courses = await fb.list_courses()
    await message.answer("Kurslar ro'yxati:", reply_markup=_courses_list_kb(courses))


# --- Tahrirlash (Edit) ---

async def _process_media(message: Message, folder: str) -> tuple[str, str, str]:
    media_type = None
    file_id = None
    ext = "bin"
    media_url = None

    if message.text:
        media_type = "link"
        media_url = message.text.strip()
    elif message.photo:
        media_type = "photo"
        file_id = message.photo[-1].file_id
        ext = "jpg"
    elif message.video:
        media_type = "video"
        file_id = message.video.file_id
        ext = "mp4"
    elif message.document:
        media_type = "document"
        file_id = message.document.file_id
        ext = (message.document.file_name or "file.pdf").split(".")[-1]
    elif message.audio:
        media_type = "audio"
        file_id = message.audio.file_id
        ext = (message.audio.file_name or "audio.mp3").split(".")[-1]
    elif message.voice:
        media_type = "voice"
        file_id = message.voice.file_id
        ext = "ogg"

    if file_id:
        media_url = file_id
        
    return media_type, media_url, ext


# 1. Qo'llanma
@router.callback_query(F.data.startswith("cedit_manual:"))
async def cedit_manual_start(callback: CallbackQuery, state: FSMContext, db_user: dict | None):
    if not _require_admin(db_user): return
    course_id = callback.data.split(":", 1)[1]
    await state.update_data(edit_course_id=course_id)
    await state.set_state(AdminCourseEdit.waiting_manual_text)
    await callback.message.answer("📖 Qo'llanma matnini yuboring:\n(Yoki to'g'ridan-to'g'ri PDF, Rasm, Video jo'natsangiz ham bo'ladi)")
    await callback.answer()

@router.message(AdminCourseEdit.waiting_manual_text, F.photo | F.document | F.video | F.audio | F.voice)
async def cedit_manual_text_media_direct(message: Message, state: FSMContext):
    caption = message.caption or ""
    data = await state.get_data()
    course_id = data["edit_course_id"]
    msg = await message.answer("Yuklanmoqda...")
    media_type, media_url, _ = await _process_media(message, course_id)
    await fb.update_course(course_id, {"manual_text": caption, "manual_media_type": media_type, "manual_media_url": media_url})
    await state.clear()
    await msg.edit_text("✅ Qo'llanma saqlandi.")

@router.message(AdminCourseEdit.waiting_manual_text, F.text)
async def cedit_manual_text(message: Message, state: FSMContext):
    await state.update_data(manual_text=message.text)
    await state.set_state(AdminCourseEdit.waiting_manual_media)
    await message.answer("Endi qo'llanma uchun fayl (masalan PDF), rasm yoki Ssilka (Link) yuboring. Yoki mediasiz saqlash tugmasini bosing:", reply_markup=_skip_media_kb())

@router.callback_query(AdminCourseEdit.waiting_manual_media, F.data == "cedit_skip_media")
async def cedit_manual_skip(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    course_id = data["edit_course_id"]
    await fb.update_course(course_id, {"manual_text": data["manual_text"], "manual_media_url": None, "manual_media_type": None})
    await state.clear()
    await callback.message.answer("✅ Qo'llanma mediasiz saqlandi.")
    await course_view(callback, {"role": "admin"}, course_id=course_id)

@router.message(AdminCourseEdit.waiting_manual_media, F.photo | F.document | F.text | F.video | F.audio | F.voice)
async def cedit_manual_media(message: Message, state: FSMContext):
    data = await state.get_data()
    course_id = data["edit_course_id"]
    msg = await message.answer("Yuklanmoqda...")
    media_type, media_url, _ = await _process_media(message, course_id)
    await fb.update_course(course_id, {"manual_text": data["manual_text"], "manual_media_type": media_type, "manual_media_url": media_url})
    await state.clear()
    await msg.edit_text("✅ Qo'llanma saqlandi.")


# 2. Video
@router.callback_query(F.data.startswith("cedit_video:"))
async def cedit_video_start(callback: CallbackQuery, state: FSMContext, db_user: dict | None):
    if not _require_admin(db_user): return
    course_id = callback.data.split(":", 1)[1]
    await state.update_data(edit_course_id=course_id)
    await state.set_state(AdminCourseEdit.waiting_lesson_num_for_video)
    await callback.message.answer("Nechanchi dars videosini kiritmoqchisiz? (Faqat raqam yozing, masalan: 1)")
    await callback.answer()

@router.message(AdminCourseEdit.waiting_lesson_num_for_video, F.text)
async def cedit_video_lesson_num(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, faqat raqam kiriting (masalan: 1)")
        return
    await state.update_data(lesson_num=int(message.text))
    await state.set_state(AdminCourseEdit.waiting_video_text)
    await message.answer(f"🎬 {message.text}-dars videosi uchun tavsif yuboring:\n(Yoki to'g'ridan-to'g'ri Videoni o'zini jo'natsangiz ham bo'ladi)")

@router.message(AdminCourseEdit.waiting_video_text, F.photo | F.document | F.video | F.audio | F.voice)
async def cedit_video_text_media_direct(message: Message, state: FSMContext):
    caption = message.caption or ""
    data = await state.get_data()
    course_id = data["edit_course_id"]
    lesson_num = data["lesson_num"]
    msg = await message.answer("Yuklanmoqda...")
    media_type, media_url, _ = await _process_media(message, course_id)
    await fb.update_course_lesson(course_id, lesson_num, {"video_text": caption, "video_media_type": media_type, "video_media_url": media_url})
    await state.clear()
    await msg.edit_text(f"✅ {lesson_num}-dars videosi saqlandi.")

@router.message(AdminCourseEdit.waiting_video_text, F.text)
async def cedit_video_text(message: Message, state: FSMContext):
    await state.update_data(video_text=message.text)
    await state.set_state(AdminCourseEdit.waiting_video_media)
    await message.answer("Endi video uchun media (Video, Ssilka, vs) yuboring:")

@router.message(AdminCourseEdit.waiting_video_media, F.photo | F.document | F.text | F.video | F.audio | F.voice)
async def cedit_video_media(message: Message, state: FSMContext):
    data = await state.get_data()
    course_id = data["edit_course_id"]
    lesson_num = data["lesson_num"]
    msg = await message.answer("Yuklanmoqda...")
    media_type, media_url, _ = await _process_media(message, course_id)
    await fb.update_course_lesson(course_id, lesson_num, {"video_text": data["video_text"], "video_media_type": media_type, "video_media_url": media_url})
    await state.clear()
    await msg.edit_text(f"✅ {lesson_num}-dars videosi saqlandi.")


# 3. Topshiriq
@router.callback_query(F.data.startswith("cedit_assignment:"))
async def cedit_assignment_start(callback: CallbackQuery, state: FSMContext, db_user: dict | None):
    if not _require_admin(db_user): return
    course_id = callback.data.split(":", 1)[1]
    await state.update_data(edit_course_id=course_id)
    await state.set_state(AdminCourseEdit.waiting_lesson_num_for_assignment)
    await callback.message.answer("Nechanchi dars topshirig'ini kiritmoqchisiz? (Faqat raqam yozing, masalan: 1)")
    await callback.answer()

@router.message(AdminCourseEdit.waiting_lesson_num_for_assignment, F.text)
async def cedit_assignment_lesson_num(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, faqat raqam kiriting (masalan: 1)")
        return
    await state.update_data(lesson_num=int(message.text))
    await state.set_state(AdminCourseEdit.waiting_assignment_text)
    await message.answer(f"📝 {message.text}-dars topshiriq matnini yuboring:\n(Yoki to'g'ridan-to'g'ri fayl/rasm jo'natsangiz ham bo'ladi)")

@router.message(AdminCourseEdit.waiting_assignment_text, F.photo | F.document | F.video | F.audio | F.voice)
async def cedit_assignment_text_media_direct(message: Message, state: FSMContext):
    caption = message.caption or ""
    data = await state.get_data()
    course_id = data["edit_course_id"]
    lesson_num = data["lesson_num"]
    msg = await message.answer("Yuklanmoqda...")
    media_type, media_url, _ = await _process_media(message, course_id)
    await fb.update_course_lesson(course_id, lesson_num, {"assignment_text": caption, "assignment_media_type": media_type, "assignment_media_url": media_url})
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, test qo'shish", callback_data="add_lesson_test:yes")
    builder.button(text="❌ Yo'q, kerak emas", callback_data="add_lesson_test:no")
    await msg.edit_text(f"✅ {lesson_num}-dars topshirig'i saqlandi. \n\nUshbu topshiriq uchun qo'shimcha Test ham qo'shasizmi?", reply_markup=builder.as_markup())

@router.message(AdminCourseEdit.waiting_assignment_text, F.text)
async def cedit_assignment_text(message: Message, state: FSMContext):
    await state.update_data(assignment_text=message.text)
    await state.set_state(AdminCourseEdit.waiting_assignment_media)
    await message.answer("Endi topshiriq uchun ixtiyoriy media (Rasm, Fayl va h.k) jo'nating. Yoki mediasiz saqlash tugmasini bosing:", reply_markup=_skip_media_kb())

@router.callback_query(AdminCourseEdit.waiting_assignment_media, F.data == "cedit_skip_media")
async def cedit_assignment_skip(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    course_id = data["edit_course_id"]
    lesson_num = data["lesson_num"]
    await fb.update_course_lesson(course_id, lesson_num, {"assignment_text": data["assignment_text"], "assignment_media_url": None, "assignment_media_type": None})
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, test qo'shish", callback_data="add_lesson_test:yes")
    builder.button(text="❌ Yo'q, kerak emas", callback_data="add_lesson_test:no")
    await callback.message.answer(f"✅ {lesson_num}-dars topshirig'i mediasiz saqlandi. \n\nUshbu topshiriq uchun qo'shimcha Test ham qo'shasizmi?", reply_markup=builder.as_markup())
    await callback.answer()

@router.message(AdminCourseEdit.waiting_assignment_media, F.photo | F.document | F.text | F.video | F.audio | F.voice)
async def cedit_assignment_media(message: Message, state: FSMContext):
    data = await state.get_data()
    course_id = data["edit_course_id"]
    lesson_num = data["lesson_num"]
    msg = await message.answer("Yuklanmoqda...")
    media_type, media_url, _ = await _process_media(message, course_id)
    await fb.update_course_lesson(course_id, lesson_num, {"assignment_text": data["assignment_text"], "assignment_media_type": media_type, "assignment_media_url": media_url})
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha, test qo'shish", callback_data="add_lesson_test:yes")
    builder.button(text="❌ Yo'q, kerak emas", callback_data="add_lesson_test:no")
    await msg.edit_text(f"✅ {lesson_num}-dars topshirig'i saqlandi. \n\nUshbu topshiriq uchun qo'shimcha Test ham qo'shasizmi?", reply_markup=builder.as_markup())


# --- Test Creation Flow ---
@router.callback_query(F.data.startswith("add_lesson_test:"))
async def add_lesson_test_choice(callback: CallbackQuery, state: FSMContext, db_user: dict | None):
    if not _require_admin(db_user): return
    choice = callback.data.split(":")[1]
    
    if choice == "no":
        data = await state.get_data()
        course_id = data.get("edit_course_id")
        await state.clear()
        await callback.message.edit_text("✅ Topshiriq to'liq saqlandi.")
        if course_id:
            await course_view(callback, db_user, course_id=course_id)
        return
        
    # Yes
    await state.update_data(test_questions=[])
    await state.set_state(AdminCourseEdit.waiting_test_question)
    await callback.message.edit_text("📝 1-savolni kiriting:")
    await callback.answer()

@router.message(AdminCourseEdit.waiting_test_question, F.text)
async def lesson_test_question(message: Message, state: FSMContext):
    await state.update_data(current_test_question=message.text)
    await state.set_state(AdminCourseEdit.waiting_test_options)
    await message.answer(
        "Variantlarni vergul bilan ajratib yozing.\n"
        "Masalan: Kitob, Daftar, Qalam, Ruchka"
    )

@router.message(AdminCourseEdit.waiting_test_options, F.text)
async def lesson_test_options(message: Message, state: FSMContext):
    options = [opt.strip() for opt in message.text.split(",") if opt.strip()]
    if len(options) < 2:
        await message.answer("Kamida 2 ta variant yozing (vergul bilan ajratib).")
        return
        
    await state.update_data(current_test_options=options)
    await state.set_state(AdminCourseEdit.waiting_test_correct_answer)
    
    opts_text = "\n".join([f"{i+1}. {o}" for i, o in enumerate(options)])
    await message.answer(
        f"Variantlar qabul qilindi:\n{opts_text}\n\n"
        "Qaysi biri to'g'ri? (Faqat raqamini yozing)"
    )

@router.message(AdminCourseEdit.waiting_test_correct_answer, F.text)
async def lesson_test_correct(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Faqat raqam yozing.")
        return
        
    data = await state.get_data()
    options = data["current_test_options"]
    idx = int(message.text) - 1
    
    if idx < 0 or idx >= len(options):
        await message.answer(f"Xato raqam. 1 dan {len(options)} gacha raqam kiriting.")
        return
        
    # Save the question
    questions = data.get("test_questions", [])
    questions.append({
        "question": data["current_test_question"],
        "options": options,
        "correct_option_index": idx
    })
    await state.update_data(test_questions=questions)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Yana savol qo'shish", callback_data="lesson_test:add_more")
    builder.button(text="✅ Testni saqlash", callback_data="lesson_test:save")
    
    await message.answer(f"✅ Savol qo'shildi. Jami savollar: {len(questions)}\nDavom etamizmi?", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("lesson_test:"))
async def lesson_test_action(callback: CallbackQuery, state: FSMContext, db_user: dict | None):
    if not _require_admin(db_user): return
    action = callback.data.split(":")[1]
    
    if action == "add_more":
        await state.set_state(AdminCourseEdit.waiting_test_question)
        data = await state.get_data()
        questions = data.get("test_questions", [])
        await callback.message.edit_text(f"📝 {len(questions) + 1}-savolni kiriting:")
    elif action == "save":
        data = await state.get_data()
        course_id = data.get("edit_course_id")
        lesson_num = data.get("lesson_num")
        questions = data.get("test_questions", [])
        
        # Merge tests into lesson
        lesson = await fb.get_course_lesson(course_id, lesson_num)
        if lesson:
            await fb.update_course_lesson(course_id, lesson_num, {"tests": questions})
            
        await state.clear()
        await callback.message.edit_text(f"🎉 Ajoyib! {lesson_num}-dars uchun topshiriq va {len(questions)} ta savollik test saqlandi.")
        if course_id:
            await course_view(callback, db_user, course_id=course_id)
