from __future__ import annotations

import asyncio
import logging
from os import getenv
from typing import Any

import urllib3
from requests import Session

from bot.services.storage import (
    FALLBACK_MODELS,
    add_message,
    get_history,
    get_user_models_async,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"


def _api_key() -> str | None:
    return getenv("OPENROUTER_API_KEY")


def _proxy() -> str | None:
    return getenv("TELEGRAM_PROXY")


SYSTEM_PROMPT = (
    "Ты дружелюбный Telegram-бот. Отвечай кратко и только по-русски. "
    "Не более 500 символов."
)


def _synced_request(
    user_message: str,
    history: list[dict[str, str]],
    models: list[str],
    system_prompt: str | None = None,
) -> str:
    key = _api_key()
    if not key:
        return "API-ключ OpenRouter не настроен."

    proxy_url = _proxy()
    prompt = system_prompt or SYSTEM_PROMPT

    for attempt in range(2):
        for model in models:
            session = Session()
            session.verify = False
            if proxy_url:
                session.proxies.update({"http": proxy_url, "https": proxy_url})
            session.headers.update({"Authorization": f"Bearer {key}"})

            payload: dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": prompt},
                    *history,
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": 300,
            }

            try:
                resp = session.post(OPENROUTER_BASE_URL, json=payload, timeout=60)
                data = resp.json()
                if "error" in data:
                    err = data.get("error", {})
                    msg = err.get("message", err)
                    logger.warning("OpenRouter error on %s: %s", model, msg)
                    session.close()
                    continue
                result = data["choices"][0]["message"]["content"] or ""
                session.close()
                return result
            except Exception:
                logger.warning(
                    "OpenRouter request failed on %s (attempt %d)",
                    model,
                    attempt + 1,
                    exc_info=True,
                )
                session.close()
                continue
        logger.info("all models failed, retrying (%d/2)", attempt + 1)

    return "Не удалось связаться с AI-сервисом."


async def ask_ai(
    user_id: int,
    user_message: str,
    save_history: bool = True,
    models: list[str] | None = None,
    system_prompt: str | None = None,
) -> str:
    if models is None:
        models = await get_user_models_async(user_id)
    if not models:
        models = FALLBACK_MODELS

    history = await get_history(user_id) if save_history else []
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(
        None,
        _synced_request,
        user_message,
        history,
        models,
        system_prompt,
    )

    if save_history:
        await add_message(user_id, "user", user_message)
        await add_message(user_id, "assistant", response)

    return response
