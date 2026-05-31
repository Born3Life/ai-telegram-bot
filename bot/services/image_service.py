from __future__ import annotations

import logging
from os import getenv

import urllib3
from requests import Session

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

HF_BASE = (
    "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
)


def _hf_token() -> str | None:
    return getenv("HF_TOKEN")


def _proxy() -> str | None:
    return getenv("TELEGRAM_PROXY")


def generate_image(prompt: str) -> bytes | str:
    """Generate an image via Hugging Face Inference API.

    Args:
        prompt: Text description of the image.

    Returns:
        Raw image bytes on success, or an error message string on failure.
    """
    token = _hf_token()
    if not token:
        return (
            "HF_TOKEN не указан в .env.\nПолучи токен: huggingface.co/settings/tokens"
        )

    session = Session()
    session.verify = False
    proxy_url = _proxy()
    if proxy_url:
        session.proxies.update({"http": proxy_url, "https": proxy_url})
    session.headers.update({"Authorization": f"Bearer {token}"})

    try:
        resp = session.post(HF_BASE, json={"inputs": prompt}, timeout=120)
        if resp.status_code == 503:
            data = resp.json()
            logger.warning("Hugging Face model loading: %s", data.get("error", ""))
            return "Модель загружается, попробуй через 30 секунд."
        if resp.status_code != 200:
            logger.error("Hugging Face error %d: %s", resp.status_code, resp.text[:200])
            return f"Ошибка {resp.status_code} при генерации."
        return resp.content
    except Exception:
        logger.exception("Hugging Face request failed")
        return "Не удалось связаться с Hugging Face."
    finally:
        session.close()
