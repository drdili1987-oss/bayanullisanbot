from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from config import ADMIN_IDS
from services import firebase_service as fb


class UserContextMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user: User | None = data.get("event_from_user")
        if tg_user is not None:
            try:
                db_user = await fb.get_user(tg_user.id)
            except Exception:
                db_user = None
            # ADMIN_IDS dan admin avtomatik qilinadi
            if tg_user.id in ADMIN_IDS:
                if db_user is None:
                    db_user = {}
                db_user["role"] = "admin"
                db_user["telegram_id"] = tg_user.id
            data["db_user"] = db_user
        else:
            data["db_user"] = None
        return await handler(event, data)
