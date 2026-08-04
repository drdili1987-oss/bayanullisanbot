from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services import firebase_service as fb
from states.states import AdminQuiz
from keyboards.inline import admin_category_kb, levels_kb

router = Router(name="admin_quizzes")

def _require_admin(db_user: dict | None) -> bool:
    return bool(db_user and db_user.get("role") == "admin")

def _quizzes_manage_kb(quizzes: list[dict]):
    builder = InlineKeyboardBuilder()
    for q in quizzes:
        title = q.get("question", "Nomsiz test")[:20] + "..."
        qid = q["id"]
        builder.button(text=f"📝 {title}", callback_data=f"quiz_view:{qid}")
        builder.button(text="🗑 O'chirish", callback_data=f"quiz_del:{qid}")
    builder.button(text="➕ Yangi test qo'shish", callback_data="quiz_add")
    builder.adjust(2)
    return builder.as_markup()

@router.message(F.text == "📝 Testlar")
async def admin_quizzes_menu(message: Message, db_user: dict | None):
    if not _require_admin(db_user):
        return
    quizzes = await fb.list_quizzes()
    text = f"Jami {len(quizzes)} ta test mavjud:" if quizzes else "Hozircha hech qanday test yo'q."
    await message.answer(text, reply_markup=_quizzes_manage_kb(quizzes))

@router.callback_query(F.data.startswith("quiz_view:"))
async def quiz_view(callback: CallbackQuery, db_user: dict | None):
    if not _require_admin(db_user):
        await callback.answer()
        return
    quiz_id = callback.data.split(":", 1)[1]
    quizzes = await fb.list_quizzes()
    quiz = next((q for q in quizzes if q["id"] == quiz_id), None)
    if not quiz:
        await callback.answer("Topilmadi.")
        return

    options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(quiz.get('options', []))])
    level = quiz.get('level', "Noma'lum")
    text = (
        f"📝 <b>Savol:</b> {quiz.get('question', '')}\n\n"
        f"📂 Bo'lim: {quiz.get('category', 'Umumiy')}\n"
        f"📊 Daraja: {level}\n\n"
        f"📋 <b>Variantlar:</b>\n{options_text}\n\n"
        f"✅ <b>To'g'ri javob:</b> {quiz.get('correct_option_index', 0) + 1}-variant"
    )
    await callback.message.answer(text)
    await callback.answer()

@router.callback_query(F.data.startswith("quiz_del:"))
async def quiz_delete(callback: CallbackQuery, db_user: dict | None):
    if not _require_admin(db_user):
        await callback.answer()
        return
    quiz_id = callback.data.split(":", 1)[1]
    await fb.delete_quiz(quiz_id)

    quizzes = await fb.list_quizzes()
    text = f"O'chirildi. Jami {len(quizzes)} ta test qoldi:" if quizzes else "Barcha testlar o'chirildi."
    try:
        await callback.message.edit_reply_markup(reply_markup=_quizzes_manage_kb(quizzes))
        await callback.message.edit_text(text, reply_markup=_quizzes_manage_kb(quizzes))
    except Exception:
        await callback.message.answer(text, reply_markup=_quizzes_manage_kb(quizzes))
    await callback.answer("O'chirildi!")

@router.callback_query(F.data == "quiz_add")
async def quiz_add_start(callback: CallbackQuery, state: FSMContext, db_user: dict | None):
    if not _require_admin(db_user):
        await callback.answer()
        return
    await state.set_state(AdminQuiz.choosing_category)
    await callback.message.answer(
        "📝 <b>Yangi test qo'shish</b>\n\n"
        "1-qadam: Qaysi bo'limga qo'shmoqchisiz?",
        reply_markup=admin_category_kb()
    )
    await callback.answer()

@router.callback_query(AdminQuiz.choosing_category, F.data.startswith("cat:"))
async def quiz_choose_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":", 1)[1]
    await state.update_data(category=category)
    await state.set_state(AdminQuiz.choosing_level)
    await callback.message.answer(
        f"✅ Bo'lim tanlandi: <b>{category}</b>\n\n"
        "2-qadam: Test darajasini tanlang:",
        reply_markup=levels_kb("uz")
    )
    await callback.answer()

@router.callback_query(AdminQuiz.choosing_level, F.data.startswith("level:"))
async def quiz_choose_level(callback: CallbackQuery, state: FSMContext):
    level = callback.data.split(":", 1)[1]
    await state.update_data(level=level)
    await state.set_state(AdminQuiz.entering_question)
    await callback.message.answer(
        f"✅ Daraja tanlandi: <b>{level}</b>\n\n"
        "3-qadam: Savol matnini kiriting:"
    )
    await callback.answer()

@router.message(AdminQuiz.entering_question, F.text)
async def quiz_enter_question(message: Message, state: FSMContext):
    await state.update_data(question=message.text.strip())
    await state.set_state(AdminQuiz.entering_options)
    await message.answer(
        "4-qadam: Variantlarni kiritng (vergul bilan ajratib):\n"
        "<i>Masalan: Qalam, Kitob, Daftar, Stol</i>"
    )

@router.message(AdminQuiz.entering_options, F.text)
async def quiz_enter_options(message: Message, state: FSMContext):
    options = [opt.strip() for opt in message.text.split(",") if opt.strip()]
    if len(options) < 2:
        await message.answer("Kamida 2 ta variant bo'lishi kerak. Iltimos, boshqatdan kiriting:")
        return
    
    await state.update_data(options=options)
    await state.set_state(AdminQuiz.entering_correct)
    
    options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
    await message.answer(
        f"Siz kiritgan variantlar:\n{options_text}\n\n"
        "5-qadam: To'g'ri variant raqamini kiriting (masalan, 2):"
    )

@router.message(AdminQuiz.entering_correct, F.text)
async def quiz_enter_correct(message: Message, state: FSMContext):
    data = await state.get_data()
    options = data["options"]
    
    try:
        correct_index = int(message.text.strip()) - 1
        if correct_index < 0 or correct_index >= len(options):
            raise ValueError
    except ValueError:
        await message.answer(f"Iltimos, 1 dan {len(options)} gacha bo'lgan raqam kiriting:")
        return
    
    quiz_id = await fb.create_quiz({
        "category": data["category"],
        "level": data["level"],
        "question": data["question"],
        "options": options,
        "correct_option_index": correct_index,
    })
    
    await state.clear()
    
    quizzes = await fb.list_quizzes()
    await message.answer(
        f"✅ Test muvaffaqiyatli saqlandi! ID: <code>{quiz_id}</code>\n"
        f"Jami {len(quizzes)} ta test:",
        reply_markup=_quizzes_manage_kb(quizzes)
    )
