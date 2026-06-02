from __future__ import annotations

import asyncio
import logging

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile

from bot.services.ai_service import ask_ai
from bot.services.image_service import generate_image
from bot.services.storage import (
    FALLBACK_MODELS,
    can_generate_image_async,
    increment_images_async,
)

logger = logging.getLogger(__name__)

router = Router()

PROMPT_TEMPLATE = (
    "You are an AI image prompt generator. "
    "Translate the user's request to English and expand with visual details "
    "(lighting, style, colors, mood). "
    "Return ONLY the English prompt, 10-50 words, no labels.\n\n{}"
)


@router.message(Command("draw"))
async def handle_draw(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    text = message.text or ""
    prompt = text.removeprefix("/draw").strip()
    if not prompt:
        await message.answer("Напиши промпт после /draw.\nПример: /draw кот в космосе")
        return

    allowed, remaining = await can_generate_image_async(user.id)
    if not allowed:
        await message.answer(
            "🎨 <b>Лимит изображений на сегодня исчерпан</b>\n\n"
            "💎 /subscribe — увеличить лимит с Premium или Pro",
        )
        return

    sent = await message.answer("🎨 Думаю над промптом...")
    logger.info("draw request from user %s: %s", user.id, prompt[:80])

    enhanced = await ask_ai(
        user.id, PROMPT_TEMPLATE.format(prompt), save_history=False, models=FALLBACK_MODELS
    ) or ""
    if not enhanced or enhanced.startswith(("Не удалось", "API-ключ")):
        logger.info("enhancement failed, using original prompt")
        image_prompt = prompt
    else:
        logger.info("enhanced prompt: %s", enhanced[:120])
        image_prompt = enhanced
    await sent.edit_text("🎨 Рисую...")
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, generate_image, image_prompt)

    await increment_images_async(user.id)

    if isinstance(result, str):
        await sent.edit_text(result)
        return

    await sent.delete()
    await message.answer_photo(
        BufferedInputFile(result, filename="image.jpg"),
        caption=f"🎨 {prompt}",
    )
