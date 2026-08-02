"""AI Texture Upscaler — 2x/4x with detail enhancement."""

from __future__ import annotations

import io
from typing import Any

from PIL import Image, ImageEnhance, ImageFilter

from app.config import get_settings
from app.services.storage import upload_bytes

settings = get_settings()


def _pil_upscale(image_bytes: bytes, scale: int, enhance: bool) -> bytes:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    new_size = (img.width * scale, img.height * scale)
    # LANCZOS + sharpen as Real-ESRGAN stand-in for MVP
    up = img.resize(new_size, Image.Resampling.LANCZOS)
    if enhance:
        up = up.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
        enhancer = ImageEnhance.Contrast(up)
        up = enhancer.enhance(1.15)
        enhancer = ImageEnhance.Color(up)
        up = enhancer.enhance(1.1)
    buf = io.BytesIO()
    up.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


async def upscale_texture(
    image_bytes: bytes,
    filename: str = "texture.png",
    scale: int = 2,
    enhance: bool = True,
) -> dict[str, Any]:
    if scale not in (2, 4):
        scale = 2

    original = Image.open(io.BytesIO(image_bytes))
    orig_w, orig_h = original.size

    if settings.USE_MOCK_AI:
        result_bytes = _pil_upscale(image_bytes, scale, enhance)
        provider = "pil"
    else:
        result_bytes = None
        provider = None
        errors: list[str] = []
        if settings.REALESRGAN_URL:
            try:
                result_bytes = await _realesrgan_upscale(image_bytes, scale)
                provider = "realesrgan"
            except Exception as exc:
                errors.append(f"realesrgan: {exc}")
        if result_bytes is None and settings.STABILITY_API_KEY:
            try:
                result_bytes = await _stability_upscale(image_bytes, scale)
                provider = "stability"
            except Exception as exc:
                errors.append(f"stability: {exc}")
        if result_bytes is None:
            detail = "; ".join(errors) if errors else "No upscale provider configured"
            raise RuntimeError(f"Texture upscale failed: {detail}")

    url = upload_bytes(result_bytes, f"upscaled_{scale}x_{filename}", "image/png", "textures")
    result_img = Image.open(io.BytesIO(result_bytes))

    return {
        "original_size": {"width": orig_w, "height": orig_h},
        "upscaled_size": {"width": result_img.width, "height": result_img.height},
        "scale": scale,
        "enhanced": enhance,
        "provider": provider,
        "url": url,
        "format": "png",
    }


async def _realesrgan_upscale(image_bytes: bytes, scale: int) -> bytes:
    """Call external Real-ESRGAN HTTP service: POST /upscale multipart image + scale."""
    import httpx

    base = settings.REALESRGAN_URL.rstrip("/")
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            f"{base}/upscale",
            files={"image": ("texture.png", image_bytes, "image/png")},
            data={"scale": str(scale)},
        )
        resp.raise_for_status()
        return resp.content


async def _stability_upscale(image_bytes: bytes, scale: int) -> bytes:
    """Stability AI upscale endpoint (optional)."""
    import httpx

    async with httpx.AsyncClient(timeout=120) as client:
        files = {"image": ("image.png", image_bytes, "image/png")}
        data = {"width": str(min(scale * 512, 2048))}
        resp = await client.post(
            "https://api.stability.ai/v2beta/stable-image/upscale/fast",
            headers={"Authorization": f"Bearer {settings.STABILITY_API_KEY}", "Accept": "image/*"},
            files=files,
            data=data,
        )
        resp.raise_for_status()
        return resp.content
