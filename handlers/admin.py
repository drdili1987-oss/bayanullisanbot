import asyncio

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services import firebase_service as fb
from states.states import AdminBroadcast
from keyboards.reply import admin_menu_kb, main_menu_kb

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
    await message.answer(f"Jami foydalanuvchilar: {len(users)} ta")


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


@router.callback_query(F.data == "admin:pending_hw")
async def admin_pending_hw(callback: CallbackQuery, db_user: dict | None):
    if not _require_admin(db_user):
        await callback.answer()
        return

    pending = await fb.list_pending_homeworks()
    if not pending:
        await callback.message.answer("Kutilayotgan uy vazifalari yo'q.")
    else:
        lines = [f"• {hw['id']} — user {hw['user_id']} — lesson {hw['lesson_id']}" for hw in pending]
        await callback.message.answer("\n".join(lines))
    await callback.answer()


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
