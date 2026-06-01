from __future__ import annotations

import logging
from os import getenv

import urllib3
from requests import Session

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

OPENROUTER_BASE = "https://openrouter.ai/api/v1/images/generations"
DOWNLOAD_TIMEOUT = 120


def _api_key() -> str | None:
    return getenv("OPENROUTER_API_KEY")


def _proxy() -> str | None:
    return getenv("TELEGRAM_PROXY")


def generate_image(prompt: str) -> bytes | str:
    """Generate an image via OpenRouter (FLUX.1-schnell).

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
        "model": "black-forest-labs/flux-1-schnell",
        "prompt": prompt,
    }

    try:
        resp = session.post(OPENROUTER_BASE, json=payload, timeout=DOWNLOAD_TIMEOUT)
        data = resp.json()

        if "error" in data:
            err = data.get("error", {})
            msg = err.get("message", str(err))
            logger.error("OpenRouter image error: %s", msg)
            return f"❌ OpenRouter: {msg}"

        image_url = data.get("data", [{}])[0].get("url")
        if not image_url:
            logger.error("no image URL in response: %s", data)
            return "❌ Не удалось получить ссылку на изображение."

        logger.info("downloading image from %s", image_url[:80])
        img_resp = session.get(image_url, timeout=DOWNLOAD_TIMEOUT)
        if img_resp.status_code != 200:
            return "❌ Ошибка загрузки изображения."
        return img_resp.content

    except Exception:
        logger.exception("OpenRouter image request failed")
        return "❌ Не удалось связаться с сервисом генерации."
    finally:
        session.close()
