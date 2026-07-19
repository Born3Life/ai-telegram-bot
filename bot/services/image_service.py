from __future__ import annotations

import json
import logging
import ssl
import time
import urllib.parse
import urllib.request
from io import BytesIO
from os import getenv

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

CTX = ssl._create_unverified_context()
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _hf_token() -> str | None:
    return getenv("HF_TOKEN") or getenv("NG_HF_TOKEN")


def _hf_image(prompt: str) -> bytes | None:
    token = _hf_token()
    if not token:
        return None

    models = [
        "black-forest-labs/FLUX.1-schnell",
        "stabilityai/stable-diffusion-3.5-large",
    ]
    for model in models:
        url = f"https://router.huggingface.co/hf-inference/models/{model}"
        payload = json.dumps({"inputs": prompt, "options": {"wait_for_model": True}}).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST",
        )
        for _ in range(2):
            try:
                with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
                    raw = r.read()
                    img = Image.open(BytesIO(raw))
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    buf = BytesIO()
                    img.save(buf, format="JPEG", quality=90)
                    logger.info("HF %s: %d bytes", model, len(buf.getvalue()))
                    return buf.getvalue()
            except urllib.error.HTTPError as e:
                body = e.read().decode()[:200]
                if e.code == 503:
                    logger.info("HF %s loading, waiting...", model)
                    time.sleep(5)
                    continue
                logger.warning("HF %s HTTP %d: %s", model, e.code, body)
                break
            except Exception as e:
                logger.warning("HF %s error: %s", model, e)
                break
    return None


def _pollinations_image(prompt: str) -> bytes | None:
    q = urllib.parse.quote(prompt[:100])
    url = f"https://image.pollinations.ai/prompt/{q}?width=1024&height=768&nologo=true&safe=false"
    for _ in range(2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
                raw = r.read()
                if not raw or len(raw) < 1000:
                    logger.warning("Pollinations: too small (%d)", len(raw) if raw else 0)
                    return None
                img = Image.open(BytesIO(raw))
                if img.mode != "RGB":
                    img = img.convert("RGB")
                buf = BytesIO()
                img.save(buf, format="JPEG", quality=90)
                logger.info("Pollinations: %d bytes", len(buf.getvalue()))
                return buf.getvalue()
        except urllib.error.HTTPError as e:
            if e.code == 402:
                logger.info("Pollinations queue full, retrying...")
                time.sleep(60)
                continue
            logger.warning("Pollinations HTTP %d: %s", e.code, e.read().decode()[:100])
            break
        except Exception as e:
            logger.warning("Pollinations error: %s", e)
            break
    return None


def _fallback_image(text: str) -> bytes:
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
    img = _hf_image(prompt)
    if img is not None:
        return img
    img = _pollinations_image(prompt)
    if img is not None:
        return img
    logger.info("all providers failed, using Pillow fallback")
    return _fallback_image(prompt)
