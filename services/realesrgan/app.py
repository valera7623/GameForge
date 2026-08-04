"""Real-ESRGAN HTTP microservice (CPU via ncnn + Mesa llvmpipe).

POST /upscale  multipart: image + scale (2|4)
Compatible with GameForge REALESRGAN_URL contract.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

BIN = Path(os.environ.get("REALESRGAN_BIN", "/opt/realesrgan/realesrgan-ncnn-vulkan"))
MODELS = Path(os.environ.get("REALESRGAN_MODELS", "/opt/realesrgan/models"))
# x4plus = sharper game textures (slower). animevideov3 = faster on CPU.
DEFAULT_MODEL = os.environ.get("REALESRGAN_MODEL", "realesrgan-x4plus")
# Smaller tiles = less RAM, more overhead. 0 = auto.
TILE = int(os.environ.get("REALESRGAN_TILE", "128"))
THREADS = os.environ.get("REALESRGAN_THREADS", "1:2:2")
TIMEOUT = int(os.environ.get("REALESRGAN_TIMEOUT", "600"))

app = FastAPI(title="Real-ESRGAN (CPU/ncnn)")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "engine": "realesrgan-ncnn-vulkan",
        "model": DEFAULT_MODEL,
        "tile": TILE,
        "bin": BIN.exists(),
        "models": MODELS.is_dir(),
    }


@app.post("/upscale")
async def upscale(
    image: UploadFile = File(...),
    scale: int = Form(2),
    model: str | None = Form(None),
):
    scale = 4 if int(scale) >= 4 else 2
    model_name = (model or DEFAULT_MODEL).strip()
    allowed = {
        "realesr-animevideov3",
        "realesrgan-x4plus",
        "realesrgan-x4plus-anime",
    }
    if model_name not in allowed:
        raise HTTPException(400, f"model must be one of {sorted(allowed)}")

    data = await image.read()
    if not data:
        raise HTTPException(400, "empty image")
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(413, "image too large (max 25MB)")

    if not BIN.is_file():
        raise HTTPException(503, f"binary missing: {BIN}")
    if not MODELS.is_dir():
        raise HTTPException(503, f"models missing: {MODELS}")

    with tempfile.TemporaryDirectory(prefix="esrgan_") as tmp:
        tmp_path = Path(tmp)
        inp = tmp_path / "in.png"
        out = tmp_path / "out.png"
        inp.write_bytes(data)

        cmd = [
            str(BIN),
            "-i",
            str(inp),
            "-o",
            str(out),
            "-n",
            model_name,
            "-s",
            str(scale),
            "-m",
            str(MODELS),
            "-f",
            "png",
            "-j",
            THREADS,
        ]
        if TILE > 0:
            cmd.extend(["-t", str(TILE)])

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                timeout=TIMEOUT,
                cwd=str(BIN.parent),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(504, f"upscale timed out after {TIMEOUT}s") from exc

        if proc.returncode != 0 or not out.is_file():
            err = (proc.stderr or proc.stdout or b"").decode("utf-8", errors="replace")[-2000:]
            raise HTTPException(500, f"realesrgan failed (code={proc.returncode}): {err}")

        return Response(content=out.read_bytes(), media_type="image/png")
