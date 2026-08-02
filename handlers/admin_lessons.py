import os
import tempfile

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services import firebase_service as fb
from states.states import AdminLesson
from keyboards.reply import admin_menu_kb

router = Router(name="admin_lessons")


def _require_admin(db_user: dict | None) -> bool:
    return bool(db_user and db_user.get("role") == "admin")


def _lessons_manage_kb(lessons: list[dict]):
    """Darslar ro'yxati + qo'shish tugmasi."""
    builder = InlineKeyboardBuilder()
    for lesson in lessons:
        title = lesson.get("title", "Nomsiz")
        lid = lesson["id"]
        builder.button(text=f"📖 {title}", callback_data=f"lesson_view:{lid}")
        builder.button(text="🗑 O'chirish", callback_data=f"lesson_del:{lid}")
    builder.button(text="➕ Yangi vazifa qo'shish", callback_data="lesson_add")
    builder.adjust(2)
    return builder.as_markup()


# ─── "📋 Uy vazifalari" tugmasi (admin menyusidan) ───────────────────────────

@router.message(F.text == "📋 Uy vazifalari")
async def admin_lessons_menu(message: Message, db_user: dict | None):
    if not _require_admin(db_user):
        return
    lessons = await fb.list_lessons()
    if lessons:
        text = f"Jami {len(lessons)} ta vazifa mavjud:"
    else:
        text = "Hozircha hech qanday vazifa yo'q."
    await message.answer(text, reply_markup=_lessons_manage_kb(lessons))


# ─── Darsni ko'rish ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("lesson_view:"))
async def lesson_view(callback: CallbackQuery, db_user: dict | None):
    if not _require_admin(db_user):
        await callback.answer()
        return
    lesson_id = callback.data.split(":", 1)[1]
    lesson = await fb.get_lesson(lesson_id)
    if not lesson:
        await callback.answer("Topilmadi.")
        return

    text = (
        f"📖 <b>{lesson.get('title', 'Nomsiz')}</b>\n\n"
        f"{lesson.get('description', '')}"
    )
    # Agar media bo'lsa
    media_url = lesson.get("media_url")
    media_type = lesson.get("media_type")

    if media_url and media_type == "photo":
        await callback.message.answer_photo(media_url, caption=text)
    elif media_url and media_type == "voice":
        await callback.message.answer_voice(media_url, caption=text)
    elif media_url and media_type == "document":
        await callback.message.answer_document(media_url, caption=text)
    else:
        await callback.message.answer(text)
    await callback.answer()


# ─── Darsni o'chirish ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("lesson_del:"))
async def lesson_delete(callback: CallbackQuery, db_user: dict | None):
    if not _require_admin(db_user):
        await callback.answer()
        return
    lesson_id = callback.data.split(":", 1)[1]
    await fb.delete_lesson(lesson_id)

    # Ro'yxatni yangilaymiz
    lessons = await fb.list_lessons()
    text = f"O'chirildi. Jami {len(lessons)} ta vazifa qoldi:" if lessons else "Barcha vazifalar o'chirildi."
    try:
        await callback.message.edit_reply_markup(reply_markup=_lessons_manage_kb(lessons))
        await callback.message.edit_text(text, reply_markup=_lessons_manage_kb(lessons))
    except Exception:
        await callback.message.answer(text, reply_markup=_lessons_manage_kb(lessons))
    await callback.answer("O'chirildi!")


# ─── Yangi vazifa qo'shish (FSM) ─────────────────────────────────────────────

@router.callback_query(F.data == "lesson_add")
async def lesson_add_start(callback: CallbackQuery, state: FSMContext, db_user: dict | None):
    if not _require_admin(db_user):
        await callback.answer()
        return
    await state.set_state(AdminLesson.entering_title)
    await callback.message.answer(
        "📝 <b>Yangi vazifa qo'shish</b>\n\n"
        "1-qadam: Dars nomini kiriting:\n"
        "<i>Masalan: Dars 1 — Alifbo, Dars 5 — Harflar</i>"
    )
    await callback.answer()


@router.message(AdminLesson.entering_title, F.text)
async def lesson_enter_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AdminLesson.entering_description)
    await message.answer(
        "2-qadam: Vazifa matnini kiriting:\n"
        "<i>Talabaga nima qilish kerakligini yozing</i>"
    )


@router.message(AdminLesson.entering_description, F.text)
async def lesson_enter_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AdminLesson.entering_media)

    builder = InlineKeyboardBuilder()
    builder.button(text="⏩ Mediasiz saqlash", callback_data="lesson_save_no_media")
    await message.answer(
        "3-qadam: Rasm, ovoz yoki fayl yuboring (ixtiyoriy)\n"
        "Yoki tugmani bosib mediasiz saqlang:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(AdminLesson.entering_media, F.data == "lesson_save_no_media")
async def lesson_save_without_media(callback: CallbackQuery, state: FSMContext, db_user: dict | None):
    data = await state.get_data()
    lesson_id = await fb.create_lesson({
        "title": data["title"],
        "description": data["description"],
        "media_type": None,
        "media_url": None,
    })
    await state.clear()

    lessons = await fb.list_lessons()
    await callback.message.answer(
        f"Vazifa saqlandi! ID: <code>{lesson_id}</code>\n"
        f"Jami {len(lessons)} ta vazifa:",
        reply_markup=_lessons_manage_kb(lessons)
    )
    await callback.answer("Saqlandi!")


@router.message(AdminLesson.entering_media, F.photo | F.voice | F.document | F.audio)
async def lesson_save_with_media(message: Message, state: FSMContext):
    data = await state.get_data()

    media_type = None
    file_id = None
    ext = "bin"

    if message.photo:
        media_type = "photo"
        file_id = message.photo[-1].file_id
        ext = "jpg"
    elif message.voice:
        media_type = "voice"
        file_id = message.voice.file_id
        ext = "ogg"
    elif message.audio:
        media_type = "audio"
        file_id = message.audio.file_id
        ext = "mp3"
    elif message.document:
        media_type = "document"
        file_id = message.document.file_id
        ext = (message.document.file_name or "file.pdf").split(".")[-1]

    # Faylni yuklaymiz
    media_url = None
    if file_id:
        try:
            file = await message.bot.get_file(file_id)
            with tempfile.TemporaryDirectory() as tmp:
                local = os.path.join(tmp, f"media.{ext}")
                await message.bot.download_file(file.file_path, local)
                dest = f"lessons/{lesson_id_tmp := data['title'].replace(' ', '_')}/{media_type}.{ext}"
                media_url = await fb.upload_file(local, dest)
        except Exception as e:
            await message.answer(f"Media yuklanmadi: {e}. Mediasiz saqlanadi.")

    lesson_id = await fb.create_lesson({
        "title": data["title"],
        "description": data["description"],
        "media_type": media_type,
        "media_url": media_url,
    })
    await state.clear()

    lessons = await fb.list_lessons()
    await message.answer(
        f"Vazifa media bilan saqlandi! ID: <code>{lesson_id}</code>\n"
        f"Jami {len(lessons)} ta vazifa:",
        reply_markup=_lessons_manage_kb(lessons)
    )
