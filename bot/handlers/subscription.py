from __future__ import annotations

import logging

from aiogram import F, Router, types
from aiogram.filters import Command

from bot.services.payment import (
    handle_pre_checkout,
    handle_successful_payment,
    send_stars_invoice,
)
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
        price = f"{info['price_stars']}⭐/мес" if info["price_stars"] else "бесплатно"
        current = " ✅ <b>Текущий</b>" if key == tier else ""
        lines.append(
            f"━━━ {info['label']}{current} ━━━\n"
            f"💬 {msgs} сообщений/день\n"
            f"🎨 {imgs} изображений/день\n"
            f"🤖 {models_line}\n"
            f"{'✏️ Свой промпт' if info['custom_prompt'] else ''}\n"
            f"💰 {price}\n",
        )

    lines.append("Выбери тариф 👇")

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="🌟 Premium — 50⭐",
                    callback_data="buy_premium",
                ),
            ],
            [
                types.InlineKeyboardButton(
                    text="🚀 Pro — 150⭐",
                    callback_data="buy_pro",
                ),
            ],
        ],
    )
    await message.answer("\n".join(lines), reply_markup=kb)


@router.callback_query(F.data.in_({"buy_premium", "buy_pro"}))
async def handle_buy(callback: types.CallbackQuery) -> None:
    user = callback.from_user
    if user is None:
        return

    tier = callback.data.replace("buy_", "")
    bot = callback.bot
    await callback.answer("Отправляю счёт...")

    try:
        await send_stars_invoice(bot, user.id, tier)
    except Exception:
        await callback.message.answer(
            "❌ Ошибка оплаты. Убедись, что в @BotFather "
            "настроены платежи (Settings → Payments → Telegram Stars).",
        )


@router.pre_checkout_query()
async def pre_checkout_handler(
    pre_checkout_query: types.PreCheckoutQuery,
) -> None:
    await handle_pre_checkout(pre_checkout_query)


@router.message(F.successful_payment)
async def payment_success(message: types.Message) -> None:
    user = message.from_user
    if user is None or message.successful_payment is None:
        return

    reply = await handle_successful_payment(
        message.bot,
        user.id,
        message.successful_payment.invoice_payload,
    )
    await message.answer(reply)
