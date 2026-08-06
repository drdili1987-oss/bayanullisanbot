from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from keyboards.reply import (
    main_menu_kb,
    admin_menu_kb,
    balogat_menu_kb,
    sher_sanati_menu_kb,
    section_action_kb
)

router = Router(name="navigation")


@router.message(F.text.in_(["📖 Sarf bo'limi", "📖 Раздел Сарф"]))
async def sarf_menu(message: Message, state: FSMContext, db_user: dict | None):
    lang = db_user.get("language", "uz") if db_user else "uz"
    await state.update_data(current_section="Sarf")
    await message.answer("Sarf bo'limidasiz. Tanlang:" if lang == "uz" else "Вы в разделе Сарф. Выберите:", reply_markup=section_action_kb(lang))


@router.message(F.text.in_(["📖 Nahv bo'limi", "📖 Раздел Нахв"]))
async def nahv_menu(message: Message, state: FSMContext, db_user: dict | None):
    lang = db_user.get("language", "uz") if db_user else "uz"
    await state.update_data(current_section="Nahv")
    await message.answer("Nahv bo'limidasiz. Tanlang:" if lang == "uz" else "Вы в разделе Нахв. Выберите:", reply_markup=section_action_kb(lang))


@router.message(F.text.in_(["📖 Balog'at bo'limi", "📖 Раздел Балага"]))
async def balogat_main_menu(message: Message, state: FSMContext, db_user: dict | None):
    lang = db_user.get("language", "uz") if db_user else "uz"
    await message.answer("Balog'at bo'limi. Qismni tanlang:" if lang == "uz" else "Раздел Балага. Выберите часть:", reply_markup=balogat_menu_kb(lang))


@router.message(F.text.in_(["Maoniy bo'limi", "Раздел Маани"]))
async def balogat_maoniy(message: Message, state: FSMContext, db_user: dict | None):
    lang = db_user.get("language", "uz") if db_user else "uz"
    await state.update_data(current_section="Balog'at - Maoniy")
    await message.answer("Maoniy bo'limidasiz. Tanlang:" if lang == "uz" else "Вы в разделе Маани. Выберите:", reply_markup=section_action_kb(lang))


@router.message(F.text.in_(["Bayon bo'limi", "Раздел Баян"]))
async def balogat_bayon(message: Message, state: FSMContext, db_user: dict | None):
    lang = db_user.get("language", "uz") if db_user else "uz"
    await state.update_data(current_section="Balog'at - Bayon")
    await message.answer("Bayon bo'limidasiz. Tanlang:" if lang == "uz" else "Вы в разделе Баян. Выберите:", reply_markup=section_action_kb(lang))


@router.message(F.text.in_(["Badiy bo'limi", "Раздел Бади'"]))
async def balogat_badiy(message: Message, state: FSMContext, db_user: dict | None):
    lang = db_user.get("language", "uz") if db_user else "uz"
    await state.update_data(current_section="Balog'at - Badiy")
    await message.answer("Badiy bo'limidasiz. Tanlang:" if lang == "uz" else "Вы в разделе Бади'. Выберите:", reply_markup=section_action_kb(lang))


@router.message(F.text.in_(["📖 She'r san'ati bo'limi", "📖 Раздел Поэзия"]))
async def sher_sanati_main_menu(message: Message, state: FSMContext, db_user: dict | None):
    lang = db_user.get("language", "uz") if db_user else "uz"
    await state.update_data(current_section="She'r san'ati")
    await message.answer("She'r san'ati bo'limidasiz. Tanlang:" if lang == "uz" else "Вы в разделе Поэзия. Выберите:", reply_markup=section_action_kb(lang))


@router.message(F.text.in_(["🔙 Orqaga", "🔙 Назад"]))
async def back_to_main_menu(message: Message, state: FSMContext, db_user: dict | None):
    lang = db_user.get("language", "uz") if db_user else "uz"
    await state.update_data(current_section=None)
    await message.answer("Asosiy menyu" if lang == "uz" else "Главное меню", reply_markup=main_menu_kb(lang))


@router.message(F.text.in_(["🏠 Bosh menu", "🏠 Главное меню"]))
async def go_to_home_menu(message: Message, state: FSMContext, db_user: dict | None):
    """Talaba yoki admin istalgan bo'limdan asosiy menyuga qaytadi."""
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
    if db_user and db_user.get("role") == "admin":
        await message.answer("👨‍🏫 Assalomu Alaykum Ustoz!", reply_markup=admin_menu_kb())
    else:
        lang = db_user.get("language", "uz") if db_user else "uz"
        name = db_user.get("full_name", "") if db_user else ""
        greeting = f"👨‍🎓 Assalomu Alaykum, {name}!" if lang == "uz" else f"👨‍🎓 Ассалому Алайкум, {name}!"
        await message.answer(greeting, reply_markup=main_menu_kb(lang))
