from __future__ import annotations

import asyncio
import logging

from aiogram import Router, types
from aiogram.filters import Command

from bot.services.ai_service import generate_shpora
from bot.services.storage import (
    can_get_shpora_async,
    increment_shpatok_async,
)

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("shpora"))
async def handle_shpora(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    text = message.text or ""
    topic = text.removeprefix("/shpora").strip()
    if not topic:
        await message.answer(
            "📚 Напиши тему после /shpora.\nПример: /shpora квадратные уравнения",
        )
        return

    allowed, remaining = await can_get_shpora_async(user.id)
    if not allowed:
        await message.answer(
            "📊 <b>Лимит шпаргалок на сегодня исчерпан</b>\n\n"
            "5 бесплатных шпаргалок в день.\n"
            "💎 /subscribe — безлимит",
        )
        return

    sent = await message.answer("🧠 Генерирую шпаргалку...")
    logger.info("shpora request from user %s: %s", user.id, topic[:80])

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, generate_shpora, topic)

    await increment_shpatok_async(user.id)

    await sent.edit_text(
        f"📘 <b>{topic}</b>\n\n{result}\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Осталось на сегодня: {remaining - 1}",
    )
