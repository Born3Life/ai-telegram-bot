from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DB_PATH = DATA_DIR / "exam_bot.db"

DAILY_LIMIT_FREE = 5


def _init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                tier TEXT NOT NULL DEFAULT 'free',
                premium_until TEXT,
                shpatok_today INTEGER DEFAULT 0,
                usage_date TEXT
            )
        """)
        conn.commit()


def _get_or_create_user(user_id: int) -> dict:
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row:
            return dict(row)
        conn.execute(
            "INSERT INTO users (user_id) VALUES (?)",
            (user_id,),
        )
        conn.commit()
    return {
        "user_id": user_id,
        "tier": "free",
        "premium_until": None,
        "shpatok_today": 0,
        "usage_date": None,
    }


def _reset_daily(user: dict) -> dict:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if user.get("usage_date") != today:
        user["shpatok_today"] = 0
        user["usage_date"] = today
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute(
                "UPDATE users SET shpatok_today = 0, usage_date = ? WHERE user_id = ?",
                (today, user["user_id"]),
            )
            conn.commit()
    return user


def can_get_shpora(user_id: int) -> tuple[bool, int]:
    user = _get_or_create_user(user_id)
    user = _reset_daily(user)

    if user["tier"] != "free":
        return True, 999

    used = user["shpatok_today"]
    remaining = DAILY_LIMIT_FREE - used
    return remaining > 0, max(remaining, 0)


def increment_shpatok(user_id: int) -> None:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            "UPDATE users SET shpatok_today = shpatok_today + 1, usage_date = ? WHERE user_id = ?",
            (today, user_id),
        )
        conn.commit()


def set_tier(user_id: int, tier: str, days: int) -> None:
    until = (datetime.utcnow() + timedelta(days=days)).isoformat()
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            "INSERT INTO users (user_id, tier, premium_until) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET tier = ?, premium_until = ?",
            (user_id, tier, until, tier, until),
        )
        conn.commit()


# ---- Async wrappers ----


async def init_db() -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _init_db)


async def can_get_shpora_async(user_id: int) -> tuple[bool, int]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, can_get_shpora, user_id)


async def increment_shpatok_async(user_id: int) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, increment_shpatok, user_id)


async def set_tier_async(user_id: int, tier: str, days: int) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, set_tier, user_id, tier, days)
