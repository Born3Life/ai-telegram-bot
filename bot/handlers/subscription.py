from __future__ import annotations

import logging

from aiogram import Router, types
from aiogram.filters import Command

from bot.services.payment import admin_id, donate_url, handle_successful_payment_admin
from bot.services.storage import TIERS, get_user_tier_async

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("subscribe"))
@router.message(Command("premium"))
async def handle_subscribe(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    tier = await get_user_tier_async(user.id)

    lines = [
        "💎 <b>AI Telegram Bot — тарифы</b>\n",
    ]
    for key, info in TIERS.items():
        msgs = "∞" if info["messages_per_day"] == -1 else str(info["messages_per_day"])
        imgs = "∞" if info["images_per_day"] == -1 else str(info["images_per_day"])
        models_line = ", ".join(m.split("/")[-1] for m in info["models"])
        price = f"{info['price_stars']} ⭐" if info["price_stars"] else "бесплатно"
        current = " ✅ <b>Текущий</b>" if key == tier else ""
        lines.append(
            f"━━━ {info['label']}{current} ━━━\n"
            f"💬 {msgs} сообщений/день\n"
            f"🎨 {imgs} изображений/день\n"
            f"🤖 {models_line}\n"
            f"{'✏️ Свой промпт' if info['custom_prompt'] else ''}\n"
            f"💰 {price}\n",
        )

    url = donate_url()

    if url:
        lines.append("👇 Оплати и напиши @ админу для активации")
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="🌟 Premium — 50⭐ (оплатить)",
                        url=url,
                    ),
                ],
                [
                    types.InlineKeyboardButton(
                        text="🚀 Pro — 150⭐ (оплатить)",
                        url=url,
                    ),
                ],
                [
                    types.InlineKeyboardButton(
                        text="📩 Написать администратору",
                        url="https://t.me/born3life",
                    ),
                ],
            ],
        )
    else:
        lines.append("📩 Напиши администратору для оплаты:")
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="📩 Написать администратору",
                        url="https://t.me/born3life",
                    ),
                ],
            ],
        )

    await message.answer("\n".join(lines), reply_markup=kb)


@router.message(Command("activate"))
async def handle_activate(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    aid = admin_id()
    if aid is None or user.id != aid:
        await message.answer("❌ Команда только для администратора.")
        return

    args = (message.text or "").strip().split()
    if len(args) != 3:
        await message.answer(
            "Использование: /activate <user_id> <tier>\n"
            "Пример: /activate 123456789 premium\n"
            "Тарифы: free, premium, pro",
        )
        return

    _, target_id, target_tier = args
    if target_tier not in TIERS:
        await message.answer(f"❌ Неверный тариф. Доступны: {', '.join(TIERS.keys())}")
        return

    try:
        uid = int(target_id)
    except ValueError:
        await message.answer("❌ user_id должен быть числом.")
        return

    reply = await handle_successful_payment_admin(uid, target_tier)
    await message.answer(reply)
