from __future__ import annotations

import asyncio
import logging

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile

from bot.services.ai_service import ask_ai
from bot.services.image_service import generate_image
from bot.services.storage import (
    can_generate_image_async,
    get_user_models_async,
    increment_images_async,
)

logger = logging.getLogger(__name__)

router = Router()

PROMPT_TEMPLATE = (
    "Translate this to English for AI image generation. "
    "Add visual details, lighting, style. "
    "Return ONLY the English prompt, no extra text:\n{}"
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

    models = await get_user_models_async(user.id)
    enhanced = await ask_ai(
        user.id, PROMPT_TEMPLATE.format(prompt), save_history=False, models=models
    ) or ""
    logger.info("enhanced prompt: %s", enhanced[:120])

    image_prompt = prompt if (not enhanced or enhanced.startswith("Не удалось")) else enhanced
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
