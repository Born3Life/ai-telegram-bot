from __future__ import annotations

import json
import logging
import ssl
import time
import urllib.request
from os import getenv

from bot.services.storage import add_message, get_history

logger = logging.getLogger(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
CTX = ssl._create_unverified_context()

SYSTEM_PROMPT = (
    "Ты дружелюбный Telegram-бот. Отвечай кратко и только по-русски. "
    "Не более 500 символов."
)


def _gemini_key() -> str | None:
    return getenv("NG_GEMINI_KEY") or getenv("GEMINI_API_KEY") or getenv("GEMINI_KEY")


def _openrouter_key() -> str | None:
    return getenv("OPENROUTER_API_KEY")


def _deepseek_key() -> str | None:
    return getenv("DEEPSEEK_API_KEY")


def _ask_gemini(system: str, user: str) -> str | None:
    key = _gemini_key()
    if not key:
        return None

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
        return None

    candidates = data.get("candidates", [])
    if not candidates:
        logger.warning("Gemini: no candidates")
        return None

    text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    if not text:
        return None

    logger.info("Gemini OK (%d chars)", len(text))
    return text


def _ask_openrouter(system: str, user: str, models: list[str]) -> str | None:
    key = _openrouter_key()
    if not key:
        return None

    for model in models:
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": 500,
        }).encode()

        req = urllib.request.Request(
            OPENROUTER_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
                data = json.loads(r.read())
            text = data["choices"][0]["message"]["content"].strip()
            logger.info("OpenRouter %s OK (%d chars)", model, len(text))
            return text
        except Exception as e:
            logger.warning("OpenRouter %s failed: %s", model, e)
            continue

    return None


def _ask_deepseek(system: str, user: str) -> str | None:
    key = _deepseek_key()
    if not key:
        return None

    payload = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": 500,
    }).encode()

    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
            data = json.loads(r.read())
        text = data["choices"][0]["message"]["content"].strip()
        logger.info("DeepSeek OK (%d chars)", len(text))
        return text
    except Exception as e:
        logger.warning("DeepSeek failed: %s", e)
        return None


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
    if response is None:
        response = _ask_deepseek(prompt, user_text)
    if response is None and models:
        response = _ask_openrouter(prompt, user_text, models)
    if response is None:
        response = "Не удалось получить ответ от AI. Попробуй позже."

    if save_history:
        await add_message(user_id, "user", user_message)
        await add_message(user_id, "assistant", response)

    return response
