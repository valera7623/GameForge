"""Lightweight Real-ESRGAN-compatible HTTP stub (PIL).

Replace with a GPU Real-ESRGAN container in production.
POST /upscale  multipart: image + scale
"""

from __future__ import annotations

import io

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import Response
from PIL import Image, ImageEnhance, ImageFilter

app = FastAPI(title="Real-ESRGAN Stub")


@app.get("/health")
def health():
    return {"status": "ok", "engine": "pil-stub"}


@app.post("/upscale")
async def upscale(image: UploadFile = File(...), scale: int = Form(2)):
    scale = 4 if int(scale) >= 4 else 2
    data = await image.read()
    img = Image.open(io.BytesIO(data)).convert("RGBA")
    up = img.resize((img.width * scale, img.height * scale), Image.Resampling.LANCZOS)
    up = up.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    up = ImageEnhance.Contrast(up).enhance(1.12)
    buf = io.BytesIO()
    up.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")
