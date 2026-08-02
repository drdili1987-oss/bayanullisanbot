from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from services import firebase_service as fb
from states.states import Registration
from keyboards.reply import language_kb, phone_kb, main_menu_kb, admin_menu_kb
from utils.texts import t

router = Router(name="registration")

LANG_MAP = {"O'zbekcha": "uz", "Русский": "ru"}


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db_user: dict | None):
    if db_user:
        lang = db_user.get("language", "uz")
        is_admin = db_user.get("role") == "admin"
        if is_admin:
            await message.answer("Admin paneliga xush kelibsiz!", reply_markup=admin_menu_kb())
        else:
            await message.answer(t("main_menu", lang), reply_markup=main_menu_kb(lang))
        return

    await state.set_state(Registration.choosing_language)
    await message.answer(t("choose_language", "uz"), reply_markup=language_kb())


@router.message(Registration.choosing_language, F.text.in_(LANG_MAP.keys()))
async def choose_language(message: Message, state: FSMContext):
    lang = LANG_MAP[message.text]
    await state.update_data(language=lang)
    await state.set_state(Registration.entering_name)
    await message.answer(t("enter_name", lang))


@router.message(Registration.entering_name, F.text)
async def enter_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data["language"]
    await state.update_data(full_name=message.text.strip())
    await state.set_state(Registration.entering_phone)
    await message.answer(t("share_phone", lang), reply_markup=phone_kb(lang))


@router.message(Registration.entering_phone, F.contact)
async def enter_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data["language"]

    await fb.create_user(
        message.from_user.id,
        {
            "full_name": data["full_name"],
            "phone_number": message.contact.phone_number,
            "language": lang,
        },
    )

    await state.clear()
    await message.answer(t("registered", lang), reply_markup=main_menu_kb(lang))
