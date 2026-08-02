"""AI Sound Designer — SFX / music via ElevenLabs, MusicGen, or synthetic WAV."""

from __future__ import annotations

import io
import math
import struct
import wave
from typing import Any

from app.config import get_settings
from app.services.storage import upload_bytes

settings = get_settings()


def _synth_wav(description: str, kind: str, mood: str, duration_sec: int) -> bytes:
    """Generate a simple procedural WAV so the pipeline works without API keys."""
    sample_rate = 22050
    n_samples = sample_rate * duration_sec
    h = sum(ord(c) for c in description) % 200

    mood_freqs = {
        "dark": (110, 165, 220),
        "heroic": (262, 330, 392),
        "calm": (196, 247, 294),
        "tense": (185, 208, 277),
        "magic": (440, 554, 659),
    }
    freqs = mood_freqs.get(mood, (220, 330, 440))

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(n_samples):
            t = i / sample_rate
            if kind == "music":
                val = (
                    0.4 * math.sin(2 * math.pi * freqs[0] * t)
                    + 0.3 * math.sin(2 * math.pi * freqs[1] * t)
                    + 0.2 * math.sin(2 * math.pi * freqs[2] * t)
                )
                # Soft envelope / LFO
                val *= 0.5 + 0.5 * math.sin(2 * math.pi * 0.5 * t)
            else:
                # Percussive / noise-ish SFX
                base = math.sin(2 * math.pi * (freqs[0] + h) * t * (1 + 0.3 * math.exp(-3 * t)))
                noise = ((i * 1103515245 + h) % 1000) / 1000.0 - 0.5
                env = math.exp(-2.5 * t / max(duration_sec, 1))
                val = (0.6 * base + 0.3 * noise) * env
            sample = int(max(-1, min(1, val)) * 32767)
            frames += struct.pack("<h", sample)
        wf.writeframes(frames)
    return buf.getvalue()


async def generate_sound(
    description: str,
    kind: str = "sfx",
    mood: str = "dark",
    duration_sec: int = 5,
) -> dict[str, Any]:
    fmt = "wav"
    content_type = "audio/wav"
    prompt = f"{mood} mood: {description}"

    if settings.USE_MOCK_AI:
        audio_bytes = _synth_wav(description, kind, mood, duration_sec)
        provider = "synthetic"
    else:
        audio_bytes = None
        provider = None
        errors: list[str] = []
        if kind == "music" and settings.REPLICATE_API_TOKEN:
            try:
                audio_bytes = await _musicgen_replicate(prompt, duration_sec)
                provider = "musicgen"
            except Exception as exc:
                errors.append(f"musicgen: {exc}")
        if kind == "sfx" and settings.ELEVENLABS_API_KEY:
            try:
                audio_bytes = await _elevenlabs_sfx(description, duration_sec)
                provider = "elevenlabs"
                fmt = "mp3"
                content_type = "audio/mpeg"
            except Exception as exc:
                errors.append(f"elevenlabs: {exc}")
        # Allow OpenAI-free music/sfx only via configured providers
        if audio_bytes is None:
            detail = "; ".join(errors) if errors else f"No provider configured for kind={kind}"
            raise RuntimeError(f"Sound generation failed: {detail}")

    filename = f"{kind}_{mood}.{fmt}"
    url = upload_bytes(audio_bytes, filename, content_type, "audio")
    return {
        "description": description,
        "kind": kind,
        "mood": mood,
        "duration_sec": duration_sec,
        "provider": provider,
        "format": fmt,
        "url": url,
    }


async def _musicgen_replicate(prompt: str, duration_sec: int) -> bytes:
    """Generate music via Replicate MusicGen API."""
    import httpx

    headers = {
        "Authorization": f"Token {settings.REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    model = settings.MUSICGEN_MODEL
    async with httpx.AsyncClient(timeout=300) as client:
        create = await client.post(
            "https://api.replicate.com/v1/predictions",
            headers=headers,
            json={
                "version": model.split(":")[-1] if ":" in model else model,
                "input": {
                    "prompt": prompt,
                    "duration": min(max(duration_sec, 1), 30),
                    "model_version": "stereo-melody-large",
                    "output_format": "wav",
                },
            },
        )
        # If version string is a full slug without version hash, use models API
        if create.status_code == 422 or create.status_code == 400:
            create = await client.post(
                "https://api.replicate.com/v1/models/meta/musicgen/predictions",
                headers=headers,
                json={
                    "input": {
                        "prompt": prompt,
                        "duration": min(max(duration_sec, 1), 30),
                        "output_format": "wav",
                    }
                },
            )
        create.raise_for_status()
        prediction = create.json()
        get_url = prediction.get("urls", {}).get("get") or f"https://api.replicate.com/v1/predictions/{prediction['id']}"

        for _ in range(60):
            import asyncio

            await asyncio.sleep(2)
            poll = await client.get(get_url, headers=headers)
            poll.raise_for_status()
            data = poll.json()
            status = data.get("status")
            if status == "succeeded":
                out = data.get("output")
                audio_url = out[0] if isinstance(out, list) else out
                if not audio_url:
                    raise RuntimeError("MusicGen returned empty output")
                audio = await client.get(audio_url)
                audio.raise_for_status()
                return audio.content
            if status in ("failed", "canceled"):
                raise RuntimeError(data.get("error") or "MusicGen failed")
        raise TimeoutError("MusicGen timed out")


async def _elevenlabs_sfx(description: str, duration_sec: int) -> bytes:
    import httpx

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://api.elevenlabs.io/v1/sound-generation",
            headers={"xi-api-key": settings.ELEVENLABS_API_KEY, "Content-Type": "application/json"},
            json={"text": description, "duration_seconds": duration_sec},
        )
        resp.raise_for_status()
        return resp.content
