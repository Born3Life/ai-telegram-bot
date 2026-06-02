from __future__ import annotations

import json
import logging
import ssl
import urllib.request
from os import getenv

from bot.services.storage import add_message, get_history

logger = logging.getLogger(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
CTX = ssl._create_unverified_context()

SYSTEM_PROMPT = (
    "Ты дружелюбный Telegram-бот. Отвечай кратко и только по-русски. "
    "Не более 500 символов."
)


def _gemini_key() -> str | None:
    return getenv("NG_GEMINI_KEY") or getenv("GEMINI_API_KEY") or getenv("GEMINI_KEY")


def _ask_gemini(system: str, user: str) -> str:
    key = _gemini_key()
    if not key:
        return "API-ключ Gemini не настроен."

    payload = json.dumps({
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": user}]}],
        "generationConfig": {"maxOutputTokens": 500, "temperature": 0.8, "topP": 0.95},
    }).encode()

    req = urllib.request.Request(
        f"{GEMINI_URL}?key={key}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
            data = json.loads(r.read())
    except Exception as e:
        logger.warning("Gemini request failed: %s", e)
        return "Не удалось связаться с AI-сервисом."

    candidates = data.get("candidates", [])
    if not candidates:
        logger.warning("Gemini: no candidates: %s", str(data)[:200])
        return "AI не дал ответа."

    text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    if not text:
        return "AI вернул пустой ответ."

    logger.info("Gemini OK (%d chars)", len(text))
    return text


async def ask_ai(
    user_id: int,
    user_message: str,
    save_history: bool = True,
    models: list[str] | None = None,
    system_prompt: str | None = None,
) -> str:
    prompt = system_prompt or SYSTEM_PROMPT

    history = await get_history(user_id) if save_history else []
    history_block = ""
    if history:
        history_block = "\n".join(
            f"{'Пользователь' if h['role'] == 'user' else 'Бот'}: {h['text']}"
            for h in history[-6:]
        )

    user_text = user_message
    if history_block:
        user_text = f"История:\n{history_block}\n\nСообщение: {user_message}"

    response = _ask_gemini(prompt, user_text)

    if save_history:
        await add_message(user_id, "user", user_message)
        await add_message(user_id, "assistant", response)

    return response
