import os
import tempfile

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_IDS
from services import firebase_service as fb
from states.states import Homework, AdminReview
from keyboards.inline import homework_review_kb, grade_kb
from keyboards.reply import main_menu_kb
from utils.texts import t

router = Router(name="homework")


@router.message(F.text.in_(["📚 Uy vazifasi", "📚 Домашнее задание"]))
async def start_homework(message: Message, state: FSMContext, db_user: dict | None):
    if not db_user:
        await message.answer(t("not_registered", "uz"))
        return
    lang = db_user["language"]

    # Firestore dan dinamik darslarni olamiz
    lessons = await fb.list_lessons()
    if not lessons:
        await message.answer(
            "Hozircha hech qanday vazifa yo'q. Admin tez orada qo'shadi!" if lang == "uz"
            else "Заданий пока нет. Администратор скоро добавит!"
        )
        return

    # Inline keyboard yasaymiz
    builder = InlineKeyboardBuilder()
    for lesson in lessons:
        builder.button(
            text=f"📖 {lesson.get('title', 'Dars')}",
            callback_data=f"lesson:{lesson['id']}"
        )
    builder.adjust(1)

    await state.set_state(Homework.choosing_lesson)
    await message.answer(t("choose_lesson", lang), reply_markup=builder.as_markup())


@router.callback_query(Homework.choosing_lesson, F.data.startswith("lesson:"))
async def choose_lesson(callback: CallbackQuery, state: FSMContext, db_user: dict):
    lesson_id = callback.data.split(":", 1)[1]
    lang = db_user.get("language", "uz")

    # Dars ma'lumotlarini ko'rsatamiz
    lesson = await fb.get_lesson(lesson_id)
    await state.update_data(lesson_id=lesson_id)
    await state.set_state(Homework.waiting_content)

    task_text = ""
    if lesson:
        task_text = f"\n\n📋 <b>Vazifa:</b>\n{lesson.get('description', '')}"

        # Agar darsda media bo'lsa — ko'rsatamiz
        media_url = lesson.get("media_url")
        media_type = lesson.get("media_type")
        if media_url and media_type == "photo":
            await callback.message.answer_photo(media_url, caption=task_text)
        elif media_url and media_type == "voice":
            await callback.message.answer_voice(media_url, caption=task_text)
        elif media_url and media_type == "document":
            await callback.message.answer_document(media_url, caption=task_text)
        else:
            await callback.message.answer(task_text)
    
    await callback.message.answer(t("send_homework", lang))
    await callback.answer()


async def _store_media(message: Message, user_id: int, kind: str, file_id: str, ext: str) -> str:
    file = await message.bot.get_file(file_id)
    with tempfile.TemporaryDirectory() as tmp_dir:
        local_path = os.path.join(tmp_dir, f"{kind}.{ext}")
        await message.bot.download_file(file.file_path, local_path)
        dest_path = fb.new_storage_path(user_id, kind, ext)
        return await fb.upload_file(local_path, dest_path)


@router.message(Homework.waiting_content, F.voice | F.audio | F.photo | F.document | F.text)
async def receive_homework(message: Message, state: FSMContext, db_user: dict):
    data = await state.get_data()
    lang = db_user["language"]
    lesson_id = data["lesson_id"]

    hw_data = {
        "user_id": message.from_user.id,
        "lesson_id": lesson_id,
        "media_type": "text",
        "file_url": None,
        "text_answer": None,
    }

    if message.voice:
        hw_data["media_type"] = "voice"
        hw_data["file_url"] = await _store_media(message, message.from_user.id, "voice", message.voice.file_id, "ogg")
    elif message.audio:
        hw_data["media_type"] = "audio"
        hw_data["file_url"] = await _store_media(message, message.from_user.id, "audio", message.audio.file_id, "mp3")
    elif message.photo:
        hw_data["media_type"] = "photo"
        hw_data["file_url"] = await _store_media(message, message.from_user.id, "photo", message.photo[-1].file_id, "jpg")
    elif message.document:
        ext = (message.document.file_name or "file.pdf").split(".")[-1]
        hw_data["media_type"] = "document"
        hw_data["file_url"] = await _store_media(message, message.from_user.id, "document", message.document.file_id, ext)
    else:
        hw_data["media_type"] = "text"
        hw_data["text_answer"] = message.text

    hw_id = await fb.create_homework(hw_data)
    await state.clear()
    await message.answer(t("homework_received", lang), reply_markup=main_menu_kb(lang))

    # Dars nomini olamiz
    lesson = await fb.get_lesson(lesson_id)
    lesson_title = lesson.get("title", lesson_id) if lesson else lesson_id
    student_name = message.from_user.full_name or str(message.from_user.id)

    caption = (
        f"📬 <b>Yangi uy vazifasi!</b>\n\n"
        f"👤 Talaba: <b>{student_name}</b> (<code>{message.from_user.id}</code>)\n"
        f"📖 Dars: <b>{lesson_title}</b>\n"
        f"📎 Tur: {hw_data['media_type']}"
    )

    for admin_id in ADMIN_IDS:
        try:
            # 1. Sarlavha xabari + baholash tugmalari
            await message.bot.send_message(
                admin_id,
                caption,
                reply_markup=homework_review_kb(hw_id),
            )
            # 2. Talabaning asıl javobini yuboramiz
            if hw_data["media_type"] == "text":
                await message.bot.send_message(
                    admin_id,
                    f"✏️ Javob:\n{hw_data['text_answer']}",
                )
            elif hw_data["media_type"] == "voice":
                await message.bot.send_voice(admin_id, voice=message.voice.file_id)
            elif hw_data["media_type"] == "audio":
                await message.bot.send_audio(admin_id, audio=message.audio.file_id)
            elif hw_data["media_type"] == "photo":
                await message.bot.send_photo(admin_id, photo=message.photo[-1].file_id)
            elif hw_data["media_type"] == "document":
                await message.bot.send_document(admin_id, document=message.document.file_id)
        except Exception:
            continue



@router.callback_query(F.data.startswith("hw_grade:"))
async def hw_grade_prompt(callback: CallbackQuery, state: FSMContext):
    hw_id = callback.data.split(":", 1)[1]
    await state.update_data(hw_id=hw_id)
    await state.set_state(AdminReview.waiting_grade)
    await callback.message.answer("Baho tanlang:", reply_markup=grade_kb(hw_id))
    await callback.answer()


@router.callback_query(F.data.startswith("hw_set_grade:"))
async def hw_set_grade(callback: CallbackQuery, state: FSMContext):
    _, hw_id, grade = callback.data.split(":")
    await fb.update_homework(hw_id, {"grade": int(grade), "status": "approved"})
    await state.update_data(hw_id=hw_id)
    await state.set_state(AdminReview.waiting_feedback)
    await callback.message.answer("Talaba uchun fikr-mulohaza yozing (matn yoki ovozli):")
    await callback.answer()


@router.callback_query(F.data.startswith("hw_reject:"))
async def hw_reject(callback: CallbackQuery):
    hw_id = callback.data.split(":", 1)[1]
    await fb.update_homework(hw_id, {"status": "rejected"})
    hw = await fb.get_homework(hw_id)
    await callback.message.bot.send_message(hw["user_id"], "Uy vazifangiz rad etildi. Iltimos qayta yuboring.")
    await callback.message.answer("Rad etildi.")
    await callback.answer()


@router.message(AdminReview.waiting_feedback, F.text | F.voice)
async def hw_feedback(message: Message, state: FSMContext):
    data = await state.get_data()
    hw_id = data["hw_id"]
    hw = await fb.get_homework(hw_id)

    if message.voice:
        file = await message.bot.get_file(message.voice.file_id)
        with tempfile.TemporaryDirectory() as tmp_dir:
            local_path = os.path.join(tmp_dir, "feedback.ogg")
            await message.bot.download_file(file.file_path, local_path)
            dest_path = fb.new_storage_path(hw["user_id"], "feedback_voice", "ogg")
            url = await fb.upload_file(local_path, dest_path)
        await fb.update_homework(hw_id, {"feedback": url})
        await message.bot.send_voice(hw["user_id"], voice=message.voice.file_id, caption="Feedback:")
    else:
        await fb.update_homework(hw_id, {"feedback": message.text})
        await message.bot.send_message(hw["user_id"], f"Feedback ({hw.get('grade')}/5): {message.text}")

    await state.clear()
    await message.answer("Fikr-mulohaza talabaga yuborildi.")
