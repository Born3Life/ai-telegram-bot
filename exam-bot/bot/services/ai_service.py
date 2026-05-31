from __future__ import annotations

import logging
from os import getenv

from requests import Session

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SHPORA_SYSTEM_PROMPT = (
    "Ты — репетитор по ОГЭ и ЕГЭ. Пользователь просит шпаргалку по теме. "
    "Напиши короткую, структурированную шпаргалку на русском языке. "
    "Используй: заголовки, списки, формулы (где нужно), примеры. "
    "Максимум 1500 символов. Без лишней воды. "
    "Если тема не связана с экзаменами, кратко объясни почему и предложи альтернативу."
)


def generate_shpora(topic: str) -> str:
    key = getenv("OPENROUTER_API_KEY")
    if not key:
        return "❌ OPENROUTER_API_KEY не настроен."

    session = Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
    )

    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {"role": "system", "content": SHPORA_SYSTEM_PROMPT},
            {"role": "user", "content": topic},
        ],
        "max_tokens": 800,
        "temperature": 0.7,
    }

    try:
        resp = session.post(OPENROUTER_URL, json=payload, timeout=30)
        data = resp.json()

        if "error" in data:
            err = data["error"]
            logger.warning("OpenRouter error: %s", err.get("message", err))
            return "❌ Сервис временно недоступен. Попробуй позже."

        content = data["choices"][0]["message"]["content"] or ""
        return (
            content.strip()
            or "❌ Не удалось сгенерировать шпаргалку. Попробуй другую тему."
        )
    except Exception:
        logger.exception("OpenRouter request failed")
        return "❌ Ошибка при генерации. Попробуй позже."
    finally:
        session.close()
