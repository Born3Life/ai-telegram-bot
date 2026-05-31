from __future__ import annotations

import logging
from os import getenv

from aiogram import Bot
from aiogram.types import LabeledPrice, PreCheckoutQuery

from bot.services.storage import TIERS, set_tier_async

logger = logging.getLogger(__name__)

INVOICE_DURATION_DAYS = 30


def admin_id() -> int | None:
    val = getenv("ADMIN_ID")
    if val:
        try:
            return int(val)
        except ValueError:
            return None
    return None


def stars_invoice(tier_key: str) -> tuple[str, str, list[LabeledPrice]]:
    info = TIERS[tier_key]
    msgs = "∞" if info["messages_per_day"] == -1 else str(info["messages_per_day"])
    imgs = "∞" if info["images_per_day"] == -1 else str(info["images_per_day"])

    title = f"{info['label']} — 1 месяц"
    description = (
        f"💬 {msgs} сообщений/день\n"
        f"🎨 {imgs} изображений/день\n"
        f"🤖 {', '.join(m.split('/')[-1] for m in info['models'])}"
    )
    prices = [LabeledPrice(label=info["label"], amount=info["price_stars"])]
    return title, description, prices


async def send_stars_invoice(bot: Bot, user_id: int, tier_key: str) -> None:
    title, desc, prices = stars_invoice(tier_key)
    await bot.send_invoice(
        chat_id=user_id,
        title=title,
        description=desc,
        payload=f"{tier_key}_{user_id}",
        provider_token="",
        currency="XTR",
        prices=prices,
    )


async def handle_pre_checkout(pre_checkout_query: PreCheckoutQuery, bot: Bot) -> None:
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


async def handle_successful_payment(user_id: int, tier_key: str) -> str:
    days = INVOICE_DURATION_DAYS
    await set_tier_async(user_id, tier_key, days)
    label = TIERS[tier_key]["label"]
    return (
        f"✅ <b>{label}</b> активирован!\n\n"
        f"Спасибо за покупку! 🎉\n"
        f"Длительность: {days} дней\n"
        "Все функции тарифа теперь доступны."
    )


async def handle_successful_payment_admin(user_id: int, tier: str) -> str:
    days = INVOICE_DURATION_DAYS
    await set_tier_async(user_id, tier, days)
    label = TIERS[tier]["label"]
    return f"✅ <b>{label}</b> активирован пользователю <code>{user_id}</code> на {days} дней."
