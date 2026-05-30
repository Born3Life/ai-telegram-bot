from __future__ import annotations

import logging
from os import getenv

from bot.services.storage import set_tier_async

logger = logging.getLogger(__name__)


def donate_url() -> str:
    return getenv("DONATE_URL", "")


def admin_id() -> int | None:
    val = getenv("ADMIN_ID")
    if val:
        try:
            return int(val)
        except ValueError:
            return None
    return None


async def handle_successful_payment_admin(user_id: int, tier: str) -> str:
    from bot.services.storage import TIERS
    days = 30
    await set_tier_async(user_id, tier, days)
    label = TIERS[tier]["label"]
    return f"✅ <b>{label}</b> активирован пользователю <code>{user_id}</code> на 30 дней."
