"""AI Texture Upscaler — 2x/4x via Real-ESRGAN or Stability Fast."""

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
    # LANCZOS + sharpen — mock / local-dev stand-in only
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


def _downscale_png(image_bytes: bytes, factor: int) -> bytes:
    """Shrink PNG by an integer factor (e.g. 4× result → 2× via factor=2)."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    if factor <= 1:
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
    new_size = (max(1, img.width // factor), max(1, img.height // factor))
    down = img.resize(new_size, Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    down.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _realesrgan_http_base() -> str:
    """Return HTTP microservice base or empty if unset / looks like a weights path."""
    base = (settings.REALESRGAN_URL or "").strip().rstrip("/")
    if not base:
        return ""
    if base.lower().endswith((".pth", ".pt", ".onnx", ".ckpt")):
        return ""
    return base


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
        if _realesrgan_http_base():
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
            if settings.is_production:
                detail = "; ".join(errors) if errors else "No upscale provider configured (Stability / Real-ESRGAN)"
                raise RuntimeError(f"Texture upscale failed: {detail}")
            # Non-prod convenience: Lanczos so local UI still works without keys.
            result_bytes = _pil_upscale(image_bytes, scale, enhance)
            provider = "pil"

    url = upload_bytes(result_bytes, f"upscaled_{scale}x_{filename}", "image/png", "textures")
    result_img = Image.open(io.BytesIO(result_bytes))
    from app.services.openai_client import record_provider_call

    if provider == "realesrgan":
        record_provider_call("realesrgan", "realesrgan")
    elif provider == "stability":
        record_provider_call("stability_image", "stability-upscale-fast")

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

    base = _realesrgan_http_base()
    # Short connect so a dead container does not block Stability fallback for minutes.
    timeout = httpx.Timeout(300.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base}/upscale",
            files={"image": ("texture.png", image_bytes, "image/png")},
            data={"scale": str(scale)},
        )
        resp.raise_for_status()
        return resp.content


async def _stability_upscale(image_bytes: bytes, scale: int) -> bytes:
    """Stability Fast Upscale — fixed 4×; for UI scale=2 downscale by 2 afterwards."""
    import httpx

    timeout = httpx.Timeout(180.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            "https://api.stability.ai/v2beta/stable-image/upscale/fast",
            headers={
                "Authorization": f"Bearer {settings.STABILITY_API_KEY}",
                "Accept": "image/*",
            },
            files={"image": ("image.png", image_bytes, "image/png")},
            # Fast endpoint has no width/height — always returns ~4×.
            data={},
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:400]}")
        result = resp.content

    if scale == 2:
        # 4× → 2× of original
        return _downscale_png(result, 2)
    return result
