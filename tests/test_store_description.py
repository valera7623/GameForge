"""Tests for AI Store Description."""

from __future__ import annotations

import re

import pytest
from httpx import AsyncClient

from app.services.ai_store_description import generate_store_description

SAMPLE = {
    "game_name": "Dungeon Explorer",
    "genre": "Action RPG",
    "platform": "PC",
    "target_audience": "hardcore",
    "usp": "Procedurally generated dungeons with deep RPG mechanics",
    "description": (
        "Dive into an endless dungeon where every run is unique. "
        "Fight monsters, find loot, and discover the secrets of the Deep."
    ),
    "key_features": [
        "Procedurally generated dungeons",
        "Deep RPG mechanics",
        "Hundreds of items and abilities",
        "Permadeath with progression",
    ],
    "target_platform": "steam",
    "language": "en",
    "tone": "epic",
}


def test_generate_store_description_en():
    result = generate_store_description(SAMPLE)
    assert result["short_description"]
    assert result["long_description"]
    assert len(result["key_features"]) >= 4
    assert len(result["tags"]) >= 3
    assert result["call_to_action"]
    assert "steam" in result["platform_specific"]
    assert "appstore" in result["platform_specific"]
    assert "<h2>" in result["steam_description"]
    assert result["target_platform"] == "steam"


def test_generate_store_description_ru():
    data = dict(SAMPLE)
    data["language"] = "ru"
    data["tone"] = "fun"
    result = generate_store_description(data)
    assert result["language"] == "ru"
    assert result["call_to_action"]
    # English inputs must still produce Russian marketing copy (not pasted EN desc).
    assert re.search(r"[А-Яа-яЁё]", result["short_description"])
    assert re.search(r"[А-Яа-яЁё]", result["long_description"])
    assert "Dive into" not in result["short_description"]
    assert "Dive into" not in result["long_description"]
    assert re.search(r"[А-Яа-яЁё]", result["call_to_action"])


def test_google_play_short_limit():
    data = dict(SAMPLE)
    data["target_platform"] = "googleplay"
    result = generate_store_description(data)
    assert len(result["short_description"]) <= 80


@pytest.mark.asyncio
async def test_store_description_api(client: AsyncClient):
    email = "store_desc@example.com"
    password = "password1234"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "SD"},
    )
    assert reg.status_code == 201, reg.text
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200

    res = await client.post("/api/v1/store-description", json=SAMPLE)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["tool"] == "store_description"
    assert body["status"] == "completed"
    assert body["output_data"]["short_description"]
