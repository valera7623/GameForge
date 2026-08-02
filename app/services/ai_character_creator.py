"""AI Character Creator — concept art via DALL-E / SD / mock SVG."""

from __future__ import annotations

import hashlib
import io
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from app.config import get_settings
from app.services.storage import upload_bytes

settings = get_settings()


def _mock_character_image(description: str, style: str) -> bytes:
    """Generate a stylized placeholder portrait when no AI keys are set."""
    h = hashlib.md5(description.encode()).hexdigest()
    # Deterministic palette from hash
    colors = [
        (int(h[i : i + 2], 16) % 180 + 40, int(h[i + 2 : i + 4], 16) % 180 + 40, int(h[i + 4 : i + 6], 16) % 180 + 40)
        for i in range(0, 12, 6)
    ]
    bg, primary, accent = colors[0], colors[1], colors[0]

    img = Image.new("RGB", (768, 1024), (18, 18, 28))
    draw = ImageDraw.Draw(img)

    # Atmosphere gradient bars
    for y in range(1024):
        shade = int(18 + (y / 1024) * 40)
        draw.line([(0, y), (768, y)], fill=(shade, shade, min(shade + 20, 60)))

    # Silhouette
    cx, cy = 384, 420
    draw.ellipse([cx - 90, cy - 120, cx + 90, cy + 60], fill=primary)  # head
    draw.ellipse([cx - 70, cy - 100, cx + 70, cy + 20], fill=(primary[0] + 20, primary[1] + 20, primary[2] + 20))
    draw.polygon(
        [(cx - 140, cy + 80), (cx + 140, cy + 80), (cx + 180, 900), (cx - 180, 900)],
        fill=accent,
    )
    # Cape / cloak hint
    draw.polygon([(cx - 100, cy + 100), (cx - 200, 950), (cx - 40, 880)], fill=primary)
    draw.polygon([(cx + 100, cy + 100), (cx + 200, 950), (cx + 40, 880)], fill=primary)

    # Frame
    draw.rectangle([24, 24, 744, 1000], outline=accent, width=4)
    draw.rectangle([40, 40, 728, 984], outline=(80, 80, 100), width=1)

    # Labels
    title = (description[:40] + "…") if len(description) > 40 else description
    draw.text((60, 60), "AI Character Creator", fill=(200, 200, 220))
    draw.text((60, 940), title, fill=(180, 180, 200))
    draw.text((60, 970), f"Style: {style}", fill=(140, 140, 160))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def create_character(description: str, style: str = "fantasy", view: str = "full_body") -> dict[str, Any]:
    image_bytes: bytes | None = None
    provider = "mock"

    if settings.OPENAI_API_KEY and not settings.USE_MOCK_AI:
        try:
            image_bytes = await _dalle_character(description, style, view)
            provider = "dall-e"
        except Exception:
            pass

    if image_bytes is None and settings.STABILITY_API_KEY and not settings.USE_MOCK_AI:
        try:
            image_bytes = await _sd_character(description, style, view)
            provider = "stable-diffusion"
        except Exception:
            pass

    if image_bytes is None:
        image_bytes = _mock_character_image(description, style)

    url = upload_bytes(image_bytes, "character.png", "image/png", "characters")
    return {
        "description": description,
        "style": style,
        "view": view,
        "provider": provider,
        "url": url,
        "width": 768,
        "height": 1024,
    }


async def _dalle_character(description: str, style: str, view: str) -> bytes:
    import base64

    from app.services.openai_client import get_openai_client

    client = get_openai_client()
    prompt = (
        f"Game character concept art, {view.replace('_', ' ')}, {style} style: {description}. "
        "Clean background, high detail, suitable as game asset reference."
    )
    resp = await client.images.generate(model="dall-e-3", prompt=prompt, size="1024x1024", response_format="b64_json")
    return base64.b64decode(resp.data[0].b64_json)


async def _sd_character(description: str, style: str, view: str) -> bytes:
    import httpx

    prompt = f"{style} game character, {view}, {description}, concept art"
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://api.stability.ai/v2beta/stable-image/generate/sd3",
            headers={"Authorization": f"Bearer {settings.STABILITY_API_KEY}", "Accept": "image/*"},
            files={"none": ""},
            data={"prompt": prompt, "output_format": "png"},
        )
        resp.raise_for_status()
        return resp.content
