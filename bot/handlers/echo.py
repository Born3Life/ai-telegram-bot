from __future__ import annotations

import logging

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.utils.markdown import hbold
from aiogram.types import ReplyKeyboardRemove

from bot.services.ai_service import ask_ai
from bot.services.storage import (
    FALLBACK_MODELS,
    can_generate_image_async,
    can_send_message_async,
    get_user_custom_prompt_async,
    get_user_tier_async,
    increment_messages_async,
)

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def handle_start(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    tier = await get_user_tier_async(user.id)
    tier_label = {"free": "Бесплатно", "premium": "Premium", "pro": "Pro"}.get(
        tier, "Free"
    )

    await message.answer(
        f"Привет, {hbold(user.full_name)}! 🤖\n\n"
        f"Твой тариф: <b>{tier_label}</b>\n"
        f"Отправь мне любое сообщение — я отвечу.\n"
        f"🎨 /draw промпт — сгенерировать изображение\n"
        f"💎 /subscribe — тарифы",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Command("profile"))
async def handle_profile(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    allowed, remaining = await can_send_message_async(user.id)
    img_allowed, img_remaining = await can_generate_image_async(user.id)
    tier = await get_user_tier_async(user.id)

    msgs = f"{remaining}/день" if remaining < 999 else "∞"
    imgs = f"{img_remaining}/день" if img_remaining < 999 else "∞"

    await message.answer(
        f"👤 <b>Профиль</b>\n\n"
        f"Тариф: <b>{tier}</b>\n"
        f"💬 Сообщений: {msgs}\n"
        f"🎨 Изображений: {imgs}\n\n"
        f"💎 /subscribe — улучшить тариф",
    )


@router.message(Command("prompt"))
async def handle_set_prompt(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    tier = await get_user_tier_async(user.id)
    if tier != "pro":
        await message.answer(
            "✏️ Свой системный промпт доступен только на тарифе Pro.\n💎 /subscribe",
        )
        return

    text = message.text or ""
    prompt = text.removeprefix("/prompt").strip()
    if not prompt:
        await message.answer(
            "Напиши промпт после /prompt.\n"
            "Пример: /prompt Ты — эксперт по Python, отвечай кодом.",
        )
        return

    from bot.services.storage import set_custom_prompt_async

    await set_custom_prompt_async(user.id, prompt)
    await message.answer(
        "✅ Системный промпт сохранён! Он будет использоваться в следующих ответах."
    )


@router.message()
async def handle_ai_response(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    text = message.text or ""
    if not text:
        await message.answer("Напиши текстовое сообщение, и я отвечу.")
        return
    if text.startswith("/"):
        return

    allowed, remaining = await can_send_message_async(user.id)
    if not allowed:
        await message.answer(
            "📦 <b>Лимит сообщений на сегодня исчерпан</b>\n\n"
            "💎 /subscribe — снять ограничения с Premium или Pro",
        )
        return

    logger.info("ai request from user %s: %s", user.id, text[:80])

    custom_prompt = await get_user_custom_prompt_async(user.id)

    sent = await message.answer("⏳ Думаю...")
    try:
        response = await ask_ai(user.id, text, system_prompt=custom_prompt, models=FALLBACK_MODELS)
    except Exception as exc:
        logger.exception("ai request failed")
        await sent.edit_text(f"❌ Ошибка: {exc}")
        return
    await increment_messages_async(user.id)
    await sent.edit_text(response or "❌ Пустой ответ от AI. Попробуй переформулировать.")
