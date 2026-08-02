from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from services import firebase_service as fb
from states.states import QuizFlow
from keyboards.inline import levels_kb, quiz_options_kb
from keyboards.reply import main_menu_kb
from utils.texts import t

router = Router(name="quiz")


@router.message(F.text.in_(["📝 Test", "📝 Тест"]))
async def start_quiz(message: Message, state: FSMContext, db_user: dict | None):
    if not db_user:
        await message.answer(t("not_registered", "uz"))
        return
    lang = db_user["language"]
    await state.set_state(QuizFlow.choosing_level)
    await message.answer(t("choose_level", lang), reply_markup=levels_kb(lang))


@router.callback_query(QuizFlow.choosing_level, F.data.startswith("level:"))
async def choose_level(callback: CallbackQuery, state: FSMContext):
    level = callback.data.split(":", 1)[1]
    questions = await fb.list_quizzes_by_level(level)

    if not questions:
        await callback.message.answer("Ushbu daraja uchun savollar topilmadi.")
        await callback.answer()
        return

    await state.update_data(level=level, questions=questions, index=0, score=0)
    await state.set_state(QuizFlow.answering)
    await callback.answer()
    await _send_question(callback.message, state)


async def _send_question(message: Message, state: FSMContext):
    data = await state.get_data()
    questions = data["questions"]
    index = data["index"]
    question = questions[index]
    await message.answer(
        f"{index + 1}. {question['question']}",
        reply_markup=quiz_options_kb(question["id"], question["options"]),
    )


@router.callback_query(QuizFlow.answering, F.data.startswith("answer:"))
async def answer_question(callback: CallbackQuery, state: FSMContext, db_user: dict):
    _, quiz_id, selected_idx = callback.data.split(":")
    selected_idx = int(selected_idx)

    data = await state.get_data()
    questions = data["questions"]
    index = data["index"]
    question = questions[index]
    score = data["score"]

    if question["id"] != quiz_id:
        await callback.answer()
        return

    correct = question["correct_option_index"] == selected_idx
    if correct:
        score += 1
        await callback.answer("✅ To'g'ri!")
    else:
        await callback.answer("❌ Noto'g'ri")

    index += 1
    await state.update_data(index=index, score=score)

    if index >= len(questions):
        lang = db_user["language"]
        await fb.record_quiz_result(callback.from_user.id, data["level"], score, len(questions))
        await callback.message.answer(
            t("quiz_finished", lang, score=score, total=len(questions)),
            reply_markup=main_menu_kb(lang),
        )
        await state.clear()
    else:
        await _send_question(callback.message, state)
