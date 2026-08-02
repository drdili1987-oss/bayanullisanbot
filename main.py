import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

from config import BOT_TOKEN, PORT
from handlers import get_root_router
from middlewares.auth import UserContextMiddleware
from webhook_server import create_webhook_app

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("main")


async def run_bot(bot: Bot, dp: Dispatcher) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def run_webhook_server(bot: Bot) -> None:
    app = create_webhook_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    log.info(f"Webhook server started on port {PORT}")
    await asyncio.Event().wait()


async def main() -> None:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(UserContextMiddleware())
    dp.include_router(get_root_router())

    await asyncio.gather(run_bot(bot, dp), run_webhook_server(bot))


if __name__ == "__main__":
    asyncio.run(main())
