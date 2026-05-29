from __future__ import annotations

import logging

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.utils.markdown import hbold

from bot.services.ai_service import ask_ai

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def handle_start(message: types.Message) -> None:
    """Send welcome message on /start command."""
    user = message.from_user
    if user is None:
        return

    await message.answer(
        f"Привет, {hbold(user.full_name)}! Я AI-бот. Отправь мне любое сообщение.",
    )


@router.message()
async def handle_ai_response(message: types.Message) -> None:
    """Respond to user message using OpenRouter AI."""
    user = message.from_user
    if user is None:
        return

    text = message.text or ""
    if not text:
        await message.answer("Напиши текстовое сообщение, и я отвечу.")
        return
    if text.startswith("/"):
        return

    logger.info("ai request from user %s: %s", user.id, text[:80])

    sent = await message.answer("⏳ Думаю...")
    response = await ask_ai(user.id, text)
    await sent.edit_text(response)
