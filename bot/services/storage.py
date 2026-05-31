from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DB_PATH = DATA_DIR / "chat_history.db"

TIERS: dict[str, dict[str, Any]] = {
    "free": {
        "label": "Бесплатно",
        "price_stars": 0,
        "messages_per_day": 10,
        "images_per_day": 2,
        "models": [
            "openrouter/free",
            "deepseek/deepseek-v4-flash:free",
        ],
        "custom_prompt": False,
    },
    "premium": {
        "label": "Premium",
        "price_stars": 50,
        "messages_per_day": -1,
        "images_per_day": 20,
        "models": [
            "openai/gpt-4o-mini",
            "openrouter/free",
        ],
        "custom_prompt": False,
    },
    "pro": {
        "label": "Pro",
        "price_stars": 150,
        "messages_per_day": -1,
        "images_per_day": -1,
        "models": [
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
        ],
        "custom_prompt": True,
    },
}

FALLBACK_MODELS = [
    "openai/gpt-4o-mini",
    "openrouter/free",
    "deepseek/deepseek-v4-flash:free",
]


def _init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_user_created
            ON messages(user_id, created_at)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                tier TEXT NOT NULL DEFAULT 'free',
                premium_until TEXT,
                messages_today INTEGER DEFAULT 0,
                images_today INTEGER DEFAULT 0,
                usage_date TEXT,
                custom_prompt TEXT
            )
        """)
        conn.commit()
    logger.info("db ready at %s", DB_PATH)


def _add_message(user_id: int, role: str, content: str) -> None:
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content),
        )
        conn.execute(
            """
            DELETE FROM messages WHERE id IN (
                SELECT id FROM messages WHERE user_id = ?
                ORDER BY id DESC LIMIT -1 OFFSET 40
            )
        """,
            (user_id,),
        )
        conn.commit()


def _get_history(user_id: int, limit: int = 20) -> list[dict[str, str]]:
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT role, content FROM messages "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def _get_or_create_user(user_id: int) -> dict[str, Any]:
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row:
            user = dict(row)
        else:
            conn.execute(
                "INSERT INTO users (user_id) VALUES (?)",
                (user_id,),
            )
            conn.commit()
            user = {
                "user_id": user_id,
                "tier": "free",
                "premium_until": None,
                "messages_today": 0,
                "images_today": 0,
                "usage_date": None,
                "custom_prompt": None,
            }
    return user


def _reset_daily_if_needed(user: dict[str, Any]) -> dict[str, Any]:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if user.get("usage_date") != today:
        user["messages_today"] = 0
        user["images_today"] = 0
        user["usage_date"] = today
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute(
                "UPDATE users SET messages_today = 0, images_today = 0, usage_date = ? WHERE user_id = ?",
                (today, user["user_id"]),
            )
            conn.commit()
    return user


def _check_tier_valid(user: dict[str, Any]) -> dict[str, Any]:
    """Downgrade expired premium users back to free."""
    if user["tier"] == "free":
        return user
    until = user.get("premium_until")
    if until:
        try:
            if datetime.utcnow() > datetime.fromisoformat(until):
                user["tier"] = "free"
                user["premium_until"] = None
                with sqlite3.connect(str(DB_PATH)) as conn:
                    conn.execute(
                        "UPDATE users SET tier = 'free', premium_until = NULL WHERE user_id = ?",
                        (user["user_id"],),
                    )
                    conn.commit()
        except (ValueError, TypeError):
            pass
    return user


def _is_admin(user_id: int) -> bool:
    from os import getenv
    val = getenv("ADMIN_ID")
    if val:
        try:
            return user_id == int(val)
        except ValueError:
            return False
    return False


def can_send_message(user_id: int) -> tuple[bool, int]:
    if _is_admin(user_id):
        return True, 999
    user = _get_or_create_user(user_id)
    user = _check_tier_valid(user)
    user = _reset_daily_if_needed(user)
    tier = TIERS.get(user["tier"], TIERS["free"])
    limit = tier["messages_per_day"]
    if limit == -1:
        return True, 999
    used = user["messages_today"]
    remaining = limit - used
    return remaining > 0, max(remaining, 0)


def can_generate_image(user_id: int) -> tuple[bool, int]:
    if _is_admin(user_id):
        return True, 999
    user = _get_or_create_user(user_id)
    user = _check_tier_valid(user)
    user = _reset_daily_if_needed(user)
    tier = TIERS.get(user["tier"], TIERS["free"])
    limit = tier["images_per_day"]
    if limit == -1:
        return True, 999
    used = user["images_today"]
    remaining = limit - used
    return remaining > 0, max(remaining, 0)


def increment_messages(user_id: int) -> None:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            """UPDATE users SET messages_today = messages_today + 1, usage_date = ?
               WHERE user_id = ?""",
            (today, user_id),
        )
        conn.commit()


def increment_images(user_id: int) -> None:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            """UPDATE users SET images_today = images_today + 1, usage_date = ?
               WHERE user_id = ?""",
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


def get_user_tier(user_id: int) -> str:
    user = _get_or_create_user(user_id)
    user = _check_tier_valid(user)
    return user["tier"]


def get_user_models(user_id: int) -> list[str]:
    user = _get_or_create_user(user_id)
    user = _check_tier_valid(user)
    tier = TIERS.get(user["tier"], TIERS["free"])
    return list(tier["models"])


def get_user_custom_prompt(user_id: int) -> str | None:
    user = _get_or_create_user(user_id)
    user = _check_tier_valid(user)
    tier = TIERS.get(user["tier"], TIERS["free"])
    if not tier["custom_prompt"]:
        return None
    return user.get("custom_prompt")


async def init_db() -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _init_db)


async def add_message(user_id: int, role: str, content: str) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _add_message, user_id, role, content)


async def get_history(user_id: int, limit: int = 20) -> list[dict[str, str]]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _get_history, user_id, limit)


async def can_send_message_async(user_id: int) -> tuple[bool, int]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, can_send_message, user_id)


async def can_generate_image_async(user_id: int) -> tuple[bool, int]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, can_generate_image, user_id)


async def increment_messages_async(user_id: int) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, increment_messages, user_id)


async def increment_images_async(user_id: int) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, increment_images, user_id)


async def set_tier_async(user_id: int, tier: str, days: int) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, set_tier, user_id, tier, days)


async def get_user_tier_async(user_id: int) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, get_user_tier, user_id)


async def get_user_models_async(user_id: int) -> list[str]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, get_user_models, user_id)


async def get_user_custom_prompt_async(user_id: int) -> str | None:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, get_user_custom_prompt, user_id)


def set_custom_prompt(user_id: int, prompt: str) -> None:
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            "UPDATE users SET custom_prompt = ? WHERE user_id = ?",
            (prompt, user_id),
        )
        conn.commit()


async def set_custom_prompt_async(user_id: int, prompt: str) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, set_custom_prompt, user_id, prompt)
