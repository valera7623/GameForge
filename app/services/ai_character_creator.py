"""AI Character Creator — concept art via GPT Image / SD / mock SVG."""

from __future__ import annotations

import hashlib
import io
from typing import Any

from PIL import Image, ImageDraw

from app.config import get_settings
from app.services.storage import upload_bytes

settings = get_settings()

# Portrait-oriented sizes supported by gpt-image-1 / 1-mini / 1.5
_IMAGE_SIZE_BY_VIEW = {
    "full_body": "1024x1536",
    "portrait": "1024x1536",
    "bust": "1024x1024",
    "face": "1024x1024",
}

# Stability AI aspect ratios (v2beta generate)
_STABILITY_ASPECT_BY_VIEW = {
    "full_body": "2:3",
    "portrait": "2:3",
    "bust": "1:1",
    "face": "1:1",
}

# STABILITY_IMAGE_MODEL → (API path segment, optional multipart `model` for /generate/sd3)
_STABILITY_GENERATE_ALIASES: dict[str, tuple[str, str | None]] = {
    "core": ("core", None),
    "ultra": ("ultra", None),
    "sd3": ("sd3", "sd3.5-large"),
    "sd3.5-large": ("sd3", "sd3.5-large"),
    "sd3-large": ("sd3", "sd3.5-large"),
    "large": ("sd3", "sd3.5-large"),
    "sd3.5-large-turbo": ("sd3", "sd3.5-large-turbo"),
    "sd3-large-turbo": ("sd3", "sd3.5-large-turbo"),
    "large-turbo": ("sd3", "sd3.5-large-turbo"),
    "turbo": ("sd3", "sd3.5-large-turbo"),
    "sd3.5-medium": ("sd3", "sd3.5-medium"),
    "sd3-medium": ("sd3", "sd3.5-medium"),
    "medium": ("sd3", "sd3.5-medium"),
    "sd3.5-flash": ("sd3", "sd3.5-flash"),
    "sd3-flash": ("sd3", "sd3.5-flash"),
    "flash": ("sd3", "sd3.5-flash"),
}


def resolve_stability_generate(model: str) -> tuple[str, str | None]:
    """Map STABILITY_IMAGE_MODEL to (path, optional sd3 `model` form field)."""
    key = (model or "core").strip().lower()
    return _STABILITY_GENERATE_ALIASES.get(key, ("core", None))


def _mock_character_image(description: str, style: str) -> bytes:
    """Generate a stylized placeholder portrait when no AI keys are set."""
    h = hashlib.md5(description.encode()).hexdigest()
    # Deterministic palette from hash
    colors = [
        (int(h[i : i + 2], 16) % 180 + 40, int(h[i + 2 : i + 4], 16) % 180 + 40, int(h[i + 4 : i + 6], 16) % 180 + 40)
        for i in range(0, 12, 6)
    ]
    primary, accent = colors[1], colors[0]

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
    if settings.USE_MOCK_AI:
        image_bytes = _mock_character_image(description, style)
        provider = "mock"
    else:
        image_bytes = None
        provider = None
        errors: list[str] = []
        mode = (settings.IMAGE_PROVIDER or "auto").strip().lower()
        try_openai = mode in ("auto", "openai") and bool(settings.OPENAI_API_KEY)
        try_stability = mode in ("auto", "stability") and bool(settings.STABILITY_API_KEY)
        # Prefer Stability when explicitly selected; otherwise OpenAI first (auto).
        order = ("stability", "openai") if mode == "stability" else ("openai", "stability")
        for name in order:
            if image_bytes is not None:
                break
            if name == "openai" and try_openai:
                try:
                    image_bytes = await _openai_character(description, style, view)
                    provider = settings.OPENAI_IMAGE_MODEL
                except Exception as exc:
                    errors.append(f"{settings.OPENAI_IMAGE_MODEL}: {exc}")
            elif name == "stability" and try_stability:
                try:
                    image_bytes = await _sd_character(description, style, view)
                    path, sd3_model = resolve_stability_generate(settings.STABILITY_IMAGE_MODEL)
                    provider = f"stability:{sd3_model or path}"
                except Exception as exc:
                    errors.append(f"stability: {exc}")
        if image_bytes is None:
            detail = "; ".join(errors) if errors else (
                "No image provider configured "
                "(set OPENAI_API_KEY and/or STABILITY_API_KEY, IMAGE_PROVIDER=auto|openai|stability)"
            )
            raise RuntimeError(f"Character generation failed: {detail}")

    size = _IMAGE_SIZE_BY_VIEW.get(view, "1024x1024")
    width, height = (int(x) for x in size.split("x"))
    if settings.USE_MOCK_AI:
        width, height = 768, 1024

    url = upload_bytes(image_bytes, "character.png", "image/png", "characters")
    return {
        "description": description,
        "style": style,
        "view": view,
        "provider": provider,
        "url": url,
        "width": width,
        "height": height,
    }


async def _openai_character(description: str, style: str, view: str) -> bytes:
    import base64

    from app.services.openai_client import get_openai_client

    client = get_openai_client()
    prompt = (
        f"Game character concept art, {view.replace('_', ' ')}, {style} style: {description}. "
        "Clean background, high detail, suitable as game asset reference."
    )
    model = settings.OPENAI_IMAGE_MODEL
    size = _IMAGE_SIZE_BY_VIEW.get(view, "1024x1024")
    kwargs: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "size": size,
    }
    # Legacy DALL·E only; gpt-image-* always returns b64_json and rejects response_format.
    if model.startswith("dall-e"):
        kwargs["response_format"] = "b64_json"
    else:
        kwargs["quality"] = "medium"
    resp = await client.images.generate(**kwargs)
    item = resp.data[0]
    b64 = getattr(item, "b64_json", None)
    if b64:
        return base64.b64decode(b64)
    # Some gateways (e.g. AITunnel docs examples) return a temporary URL instead.
    url = getattr(item, "url", None)
    if url:
        import httpx

        async with httpx.AsyncClient(timeout=120) as http:
            dl = await http.get(url)
            if dl.status_code >= 400:
                raise RuntimeError(f"Image download failed: HTTP {dl.status_code}")
            return dl.content
    raise RuntimeError("Image provider returned empty payload")


async def _sd_character(description: str, style: str, view: str) -> bytes:
    """Cloud Stability AI generate (core / ultra / SD 3.5 via /sd3) — no self-hosted SD."""
    import httpx

    path, sd3_model = resolve_stability_generate(settings.STABILITY_IMAGE_MODEL)
    prompt = (
        f"Game character concept art, {view.replace('_', ' ')}, {style} style: {description}. "
        "Clean background, high detail, suitable as game asset reference."
    )
    aspect = _STABILITY_ASPECT_BY_VIEW.get(view, "1:1")
    data: dict[str, Any] = {
        "prompt": prompt,
        "output_format": "png",
        "aspect_ratio": aspect,
    }
    if sd3_model:
        data["model"] = sd3_model
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            f"https://api.stability.ai/v2beta/stable-image/generate/{path}",
            headers={"Authorization": f"Bearer {settings.STABILITY_API_KEY}", "Accept": "image/*"},
            files={"none": ""},
            data=data,
        )
        if resp.status_code >= 400:
            detail = resp.text[:500]
            raise RuntimeError(f"HTTP {resp.status_code}: {detail}")
        return resp.content
