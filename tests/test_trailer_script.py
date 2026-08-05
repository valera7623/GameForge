"""Tests for AI Trailer Script."""

from __future__ import annotations

import re

import pytest
from httpx import AsyncClient

from app.services.ai_trailer_script import generate_trailer_script

SAMPLE = {
    "game_name": "Dungeon Explorer",
    "genre": "Action RPG",
    "description": "Procedurally generated dungeon crawler with deep RPG mechanics",
    "trailer_type": "launch",
    "duration": 60,
    "tone": "epic",
    "key_features": [
        "Procedurally generated dungeons",
        "Deep RPG mechanics",
        "Hundreds of items and abilities",
        "Permadeath with progression",
    ],
    "target_audience": "hardcore gamers",
    "platform": "PC, Console",
    "release_date": "2026-09-15",
    "lang": "en",
}


def test_generate_trailer_script_en():
    result = generate_trailer_script(SAMPLE)
    assert result["duration"] == 60
    assert len(result["scenes"]) >= 3
    assert result["voiceover"]["full_text"]
    assert result["structure"]
    assert result["text_overlays"]
    assert result["sound_design"]["music"]
    total = sum(s["duration_seconds"] for s in result["scenes"])
    assert total == 60


def test_generate_trailer_script_ru_teaser():
    data = dict(SAMPLE)
    data["lang"] = "ru"
    data["trailer_type"] = "teaser"
    data["duration"] = 20
    data["tone"] = "mysterious"
    result = generate_trailer_script(data)
    assert result["lang"] == "ru"
    assert result["duration"] == 20
    assert re.search(r"[А-Яа-яЁё]", result["voiceover"]["full_text"])
    assert re.search(r"[А-Яа-яЁё]", result["scenes"][0]["visual"])


@pytest.mark.asyncio
async def test_trailer_script_api(client: AsyncClient):
    email = "trailer_script@example.com"
    password = "password1234"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "TS"},
    )
    assert reg.status_code == 201, reg.text
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200

    res = await client.post("/api/v1/trailer-script", json=SAMPLE)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["tool"] == "trailer_script"
    assert body["status"] == "completed"
    assert body["output_data"]["scenes"]
