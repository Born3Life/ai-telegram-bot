from __future__ import annotations

import asyncio
import logging
import sys
from os import getenv
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from bot.handlers import routers  # noqa: E402
from bot.services.storage import init_db  # noqa: E402

BOT_TOKEN: str | None = getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


async def _health_handler(_request: web.Request) -> web.Response:
    return web.Response(text="ok")


async def _health_server(port: int) -> None:
    """Minimal HTTP server so Render doesn't kill the process."""
    app = web.Application()
    app.router.add_get("/health", _health_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("health server listening on port %d", port)

    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        await site.stop()
        await runner.cleanup()


async def main() -> None:
    """Initialize bot, health server (if on Render), start polling."""
    if not BOT_TOKEN:
        msg = "BOT_TOKEN is not set in .env"
        raise RuntimeError(msg)

    port = getenv("PORT")
    health_task: asyncio.Task | None = None
    if port:
        health_task = asyncio.create_task(_health_server(int(port)))

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    for router in routers:
        dp.include_router(router)

    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("bot started")
    await dp.start_polling(bot, polling_timeout=1)

    if health_task:
        health_task.cancel()
        try:
            await health_task
        except asyncio.CancelledError:
            pass
