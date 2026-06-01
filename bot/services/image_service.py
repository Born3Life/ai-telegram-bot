from __future__ import annotations

import base64
import logging
from os import getenv

import urllib3
from requests import Session

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

OPENROUTER_CHAT = "https://openrouter.ai/api/v1/chat/completions"
TIMEOUT = 120


def _api_key() -> str | None:
    return getenv("OPENROUTER_API_KEY")


def _proxy() -> str | None:
    return getenv("TELEGRAM_PROXY")


def generate_image(prompt: str) -> bytes | str:
    """Generate an image via OpenRouter chat completions (FLUX.1-schnell).

    Args:
        prompt: Text description of the image.

    Returns:
        Raw image bytes on success, or an error message string on failure.
    """
    key = _api_key()
    if not key:
        return "OPENROUTER_API_KEY не указан."

    proxy_url = _proxy()
    session = Session()
    session.verify = False
    if proxy_url:
        session.proxies.update({"http": proxy_url, "https": proxy_url})
    session.headers.update({
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    })

    payload = {
        "model": "black-forest-labs/flux.2-flex",
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["image"],
    }

    try:
        resp = session.post(OPENROUTER_CHAT, json=payload, timeout=TIMEOUT)
        data = resp.json()

        if "error" in data:
            err = data.get("error", {})
            msg = err.get("message", str(err))
            logger.error("OpenRouter image error: %s", msg)
            return f"❌ OpenRouter: {msg}"

        images = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("images", [])
        )
        if not images:
            logger.error("no images in response: %s", str(data)[:300])
            return "❌ Модель не вернула изображение."

        raw_url = images[0].get("image_url", {}).get("url", "")
        if not raw_url:
            return "❌ Пустой URL изображения."

        if raw_url.startswith("data:image"):
            _, b64_data = raw_url.split(",", 1)
            logger.info("decoding base64 image (%d chars)", len(b64_data))
            return base64.b64decode(b64_data)

        logger.info("downloading image from %s", raw_url[:80])
        img_resp = session.get(raw_url, timeout=TIMEOUT)
        if img_resp.status_code != 200:
            return "❌ Ошибка загрузки изображения."
        return img_resp.content

    except Exception:
        logger.exception("OpenRouter image request failed")
        return "❌ Не удалось связаться с сервисом генерации."
    finally:
        session.close()
