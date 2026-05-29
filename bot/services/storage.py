from __future__ import annotations

import asyncio
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DB_PATH = DATA_DIR / "chat_history.db"


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
        conn.commit()
    logger.info("chat history db ready at %s", DB_PATH)


def _add_message(user_id: int, role: str, content: str) -> None:
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content),
        )
        conn.execute("""
            DELETE FROM messages WHERE id IN (
                SELECT id FROM messages WHERE user_id = ?
                ORDER BY id DESC LIMIT -1 OFFSET 40
            )
        """, (user_id,))
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


async def init_db() -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _init_db)


async def add_message(user_id: int, role: str, content: str) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _add_message, user_id, role, content)


async def get_history(user_id: int, limit: int = 20) -> list[dict[str, str]]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _get_history, user_id, limit)
