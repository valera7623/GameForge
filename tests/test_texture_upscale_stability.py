"""Texture upscaler — Stability Fast 4× with optional 2× downscale."""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest
from PIL import Image

from app.services.ai_texture_upscaler import _downscale_png, _stability_upscale


def _png_bytes(w: int, h: int) -> bytes:
    img = Image.new("RGBA", (w, h), (40, 120, 200, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_downscale_png_halves_dimensions():
    src = _png_bytes(64, 48)
    out = _downscale_png(src, 2)
    img = Image.open(io.BytesIO(out))
    assert img.size == (32, 24)


@pytest.mark.asyncio
async def test_stability_upscale_scale2_downscales_from_4x(monkeypatch):
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "STABILITY_API_KEY", "test-key", raising=False)

    # Pretend Stability Fast returned a 4× image (128×128 from 32×32).
    four_x = _png_bytes(128, 128)

    class FakeResp:
        status_code = 200
        content = four_x
        text = ""

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **k):
            return FakeResp()

    with patch("httpx.AsyncClient", FakeClient):
        out = await _stability_upscale(_png_bytes(32, 32), scale=2)

    img = Image.open(io.BytesIO(out))
    assert img.size == (64, 64)


@pytest.mark.asyncio
async def test_stability_upscale_scale4_keeps_4x(monkeypatch):
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "STABILITY_API_KEY", "test-key", raising=False)

    four_x = _png_bytes(128, 128)

    class FakeResp:
        status_code = 200
        content = four_x
        text = ""

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **k):
            return FakeResp()

    with patch("httpx.AsyncClient", FakeClient):
        out = await _stability_upscale(_png_bytes(32, 32), scale=4)

    img = Image.open(io.BytesIO(out))
    assert img.size == (128, 128)
