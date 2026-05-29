from __future__ import annotations

import asyncio
import logging

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile

from bot.services.ai_service import ask_ai
from bot.services.image_service import generate_image

logger = logging.getLogger(__name__)

router = Router()

PROMPT_TEMPLATE = (
    "Translate this to English for AI image generation. "
    "Add visual details, lighting, style. "
    "Return ONLY the English prompt, no extra text:\n{}"
)


@router.message(Command("draw"))
async def handle_draw(message: types.Message) -> None:
    """Generate an image from a text prompt via Hugging Face."""
    user = message.from_user
    if user is None:
        return

    text = message.text or ""
    prompt = text.removeprefix("/draw").strip()
    if not prompt:
        await message.answer("Напиши промпт после /draw.\nПример: /draw кот в космосе")
        return

    sent = await message.answer("🎨 Думаю над промптом...")
    logger.info("draw request from user %s: %s", user.id, prompt[:80])

    # Enhance prompt via text AI (translate + add quality terms)
    enhanced = await ask_ai(user.id, PROMPT_TEMPLATE.format(prompt), save_history=False)
    logger.info("enhanced prompt: %s", enhanced[:120])

    await sent.edit_text("🎨 Рисую...")
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, generate_image, enhanced)

    if isinstance(result, str):
        await sent.edit_text(result)
        return

    await sent.delete()
    await message.answer_photo(
        BufferedInputFile(result, filename="image.jpg"),
        caption=f"🎨 {prompt}",
    )
