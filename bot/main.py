from __future__ import annotations

import asyncio
import logging
import os
import sys
from os import getenv
from pathlib import Path

from aiogram import Bot, Dispatcher, __version__
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import SERVER_SOFTWARE, USER_AGENT, AiohttpSession
from aiogram.enums import ParseMode
from aiohttp import ClientSession, TCPConnector
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from bot.handlers import routers  # noqa: E402
from bot.services.storage import init_db  # noqa: E402

BOT_TOKEN: str | None = getenv("BOT_TOKEN")
TELEGRAM_PROXY: str | None = getenv("TELEGRAM_PROXY")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


class ProxySession(AiohttpSession):
    """AiohttpSession with proxy support via trust_env and fresh connections."""

    async def create_session(self) -> ClientSession:
        if self._should_reset_connector:
            await self.close()

        if self._session is None or self._session.closed:
            ssl_ctx = self._connector_init.get("ssl")
            self._session = ClientSession(
                connector=TCPConnector(force_close=True, limit=1, ssl=ssl_ctx),  # type: ignore[arg-type]
                headers={USER_AGENT: f"{SERVER_SOFTWARE} aiogram/{__version__}"},
                trust_env=True,
            )
            self._should_reset_connector = False

        return self._session


async def main() -> None:
    """Initialize bot and dispatcher, register routers, start polling."""
    if not BOT_TOKEN:
        msg = "BOT_TOKEN is not set in .env"
        raise RuntimeError(msg)

    if TELEGRAM_PROXY:
        os.environ["HTTP_PROXY"] = TELEGRAM_PROXY
        os.environ["HTTPS_PROXY"] = TELEGRAM_PROXY

    bot = Bot(
        token=BOT_TOKEN,
        session=ProxySession(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    for router in routers:
        dp.include_router(router)

    await init_db()
    logger.info("bot started")
    await dp.start_polling(bot, polling_timeout=1)


if __name__ == "__main__":
    asyncio.run(main())
