from __future__ import annotations

import logging
from os import getenv

from aiogram import Bot
from aiogram.types import LabeledPrice, PreCheckoutQuery

from bot.services.storage import TIERS, set_tier_async

logger = logging.getLogger(__name__)


async def send_stars_invoice(bot: Bot, user_id: int, tier: str) -> None:
    info = TIERS[tier]
    prices = [LabeledPrice(label=info["label"], amount=info["price_stars"])]
    await bot.send_invoice(
        chat_id=user_id,
        title=info["label"],
        description=f"Подписка {info['label']} — {info['price_stars']} Telegram Stars",
        provider_token="",
        currency="XTR",
        prices=prices,
        payload=f"{tier}_subscription",
    )


async def handle_pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    await pre_checkout_query.answer(ok=True)


async def handle_successful_payment(
    bot: Bot,
    user_id: int,
    payload: str,
) -> str:
    tier = payload.replace("_subscription", "")
    if tier not in TIERS:
        return "❌ Неизвестный тариф."
    days = 30
    await set_tier_async(user_id, tier, days)
    label = TIERS[tier]["label"]
    return (
        f"✅ <b>{label} активирован!</b>\n"
        f"Действует 30 дней.\n\n"
        f"Спасибо за поддержку! 🙌"
    )
