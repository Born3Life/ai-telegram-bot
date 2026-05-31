from __future__ import annotations

import logging

from aiogram import F, Router, types
from aiogram.filters import Command

from bot.services.payment import (
    admin_id,
    handle_pre_checkout,
    handle_successful_payment,
    handle_successful_payment_admin,
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

    buttons: list[list[types.InlineKeyboardButton]] = []

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

        if key != "free":
            buttons.append(
                [
                    types.InlineKeyboardButton(
                        text=f"💳 Купить {info['label']} — {info['price_stars']}⭐",
                        callback_data=f"buy_{key}",
                    ),
                ]
            )

    buttons.append(
        [
            types.InlineKeyboardButton(
                text="📩 Написать администратору",
                url="https://t.me/born3life",
            ),
        ]
    )

    kb = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("\n".join(lines), reply_markup=kb)


@router.callback_query(F.data.startswith("buy_"))
async def handle_buy_callback(callback: types.CallbackQuery) -> None:
    user = callback.from_user
    if user is None:
        return

    tier_key = callback.data.removeprefix("buy_")
    if tier_key not in TIERS or tier_key == "free":
        await callback.answer("❌ Неверный тариф", show_alert=True)
        return

    bot = callback.bot
    await callback.answer("Отправляю счёт...")

    try:
        await send_stars_invoice(bot, user.id, tier_key)
    except Exception as exc:
        logger.exception("invoice failed for user %s tier %s", user.id, tier_key)
        await callback.message.answer(
            "❌ Ошибка при создании счёта. "
            "Убедись, что у бота включены платежи Telegram Stars в @BotFather.",
        )


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: types.PreCheckoutQuery) -> None:
    await handle_pre_checkout(pre_checkout_query, pre_checkout_query.bot)


@router.message(F.successful_payment)
async def payment_success(message: types.Message) -> None:
    user = message.from_user
    if user is None or message.successful_payment is None:
        return

    payload = message.successful_payment.invoice_payload
    try:
        tier_key, user_id_str = payload.rsplit("_", 1)
        uid = int(user_id_str)
    except (ValueError, AttributeError):
        logger.warning("invalid invoice payload: %s", payload)
        await message.answer("❌ Ошибка обработки платежа. Напиши администратору.")
        return

    if uid != user.id:
        logger.warning(
            "user %s tried to claim payment for invoice %s",
            user.id,
            payload,
        )
        await message.answer("❌ Ошибка: неверный пользователь.")
        return

    reply = await handle_successful_payment(uid, tier_key)
    await message.answer(reply)


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
