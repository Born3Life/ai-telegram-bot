from __future__ import annotations

import logging
from io import BytesIO
from os import getenv

import urllib3
from PIL import Image, ImageDraw, ImageFont
from requests import Session

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

HF_BASE = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _hf_token() -> str | None:
    return getenv("HF_TOKEN") or getenv("NG_HF_TOKEN")


def _fallback_image(text: str) -> bytes:
    """Generate gradient + text overlay (fallback if HF fails)."""
    W, H = 1024, 768
    c1, c2 = (30, 40, 80), (60, 80, 160)
    img = Image.new("RGB", (W, H), c1)
    draw = ImageDraw.Draw(img)
    for y in range(H):
        r = int(c1[0] + (c2[0] - c1[0]) * y / H)
        g = int(c1[1] + (c2[1] - c1[1]) * y / H)
        b = int(c1[2] + (c2[2] - c1[2]) * y / H)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    bar_h = int(H * 0.30)
    overlay = Image.new("RGBA", (W, bar_h), (255, 255, 255, 220))
    img.paste(overlay, (0, 0), overlay)
    font = None
    for path in [FONT_PATH, FONT_FALLBACK]:
        for size in range(40, 18, -2):
            try:
                font = ImageFont.truetype(path, size)
                break
            except OSError:
                continue
        if font:
            break
    if not font:
        try:
            font = ImageFont.load_default()
        except Exception:
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return buf.getvalue()
    text = text[:120]
    lines = []
    for line in text.split("\n"):
        if draw.textlength(line, font=font) > W - 40:
            words = line.split()
            cur = ""
            for w in words:
                test = (cur + " " + w).strip()
                if draw.textlength(test, font=font) > W - 40:
                    lines.append(cur)
                    cur = w
                else:
                    cur = test
            if cur:
                lines.append(cur)
        else:
            lines.append(line)
    y = (bar_h - len(lines) * (size + 4)) // 2 + 4
    for line in lines:
        tw = draw.textlength(line, font=font)
        x = (W - tw) // 2
        draw.text((x, y), line, font=font, fill=(20, 20, 20))
        y += size + 4
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def generate_image(prompt: str) -> bytes | str:
    """Generate image via Hugging Face Inference API (FLUX.1-schnell).
    Falls back to Pillow gradient if HF fails.

    Args:
        prompt: Text description of the image.

    Returns:
        Raw image bytes on success, or an error message string on failure.
    """
    token = _hf_token()
    if token:
        session = Session()
        session.verify = False
        proxy_url = getenv("TELEGRAM_PROXY")
        if proxy_url:
            session.proxies.update({"http": proxy_url, "https": proxy_url})
        session.headers.update({"Authorization": f"Bearer {token}"})

        try:
            resp = session.post(HF_BASE, json={"inputs": prompt}, timeout=60)
            if resp.status_code == 200:
                content_type = resp.headers.get("Content-Type", "")
                if "image" in content_type:
                    logger.info("HF image OK: %d bytes", len(resp.content))
                    session.close()
                    return resp.content
                logger.warning("HF returned non-image: %s", content_type)
            else:
                logger.warning("HF error %d: %s", resp.status_code, resp.text[:100])
        except Exception as e:
            logger.warning("HF request failed: %s", e)
        finally:
            session.close()
    else:
        logger.info("HF_TOKEN not set, using fallback")

    logger.info("fallback to Pillow gradient")
    return _fallback_image(prompt)
    text = prompt[:120]
    lines = []
    for line in text.split("\n"):
        if draw.textlength(line, font=font) > W - 40:
            words = line.split()
            cur = ""
            for w in words:
                test = (cur + " " + w).strip()
                if draw.textlength(test, font=font) > W - 40:
                    lines.append(cur)
                    cur = w
                else:
                    cur = test
            if cur:
                lines.append(cur)
        else:
            lines.append(line)
    y = (bar_h - len(lines) * (size + 4)) // 2 + 4
    for line in lines:
        tw = draw.textlength(line, font=font)
        x = (W - tw) // 2
        draw.text((x, y), line, font=font, fill=(20, 20, 20))
        y += size + 4
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()
