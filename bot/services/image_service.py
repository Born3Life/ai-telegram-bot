from __future__ import annotations

import logging
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def generate_image(prompt: str) -> bytes | str:
    """Generate an image with gradient background and text overlay.
    No API keys needed — uses Pillow.

    Args:
        prompt: Text to display on the image.

    Returns:
        Raw JPEG bytes on success, or an error message string on failure.
    """
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
