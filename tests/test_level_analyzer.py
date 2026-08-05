"""Tests for AI Level Analyzer."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.ai_level_analyzer import analyze_level, compare_levels

SAMPLE = {
    "level_name": "The Sunken Temple",
    "width": 10,
    "height": 10,
    "tiles": [
        list("WWWWWWWWWW"),
        list("W        W"),
        list("W   E    W"),
        list("W        W"),
        list("W   WWW  W"),
        list("W        W"),
        list("W        W"),
        list("W        W"),
        list("W        W"),
        list("WWWWWWWWWW"),
    ],
    "entities": [
        {"type": "start", "x": 1, "y": 1},
        {"type": "end", "x": 8, "y": 8},
        {"type": "enemy", "x": 4, "y": 2, "name": "Skeleton", "health": 50, "damage": 10},
        {"type": "enemy", "x": 6, "y": 6, "name": "Water Elemental", "health": 120, "damage": 25},
        {"type": "treasure", "x": 3, "y": 3, "value": 100},
        {"type": "trap", "x": 5, "y": 5, "damage": 20},
    ],
    "time_limit": 300,
}


def test_analyze_level_path_exists():
    result = analyze_level(SAMPLE, lang="en")
    assert result["analysis"]["path_exists"] is True
    assert result["analysis"]["path_length"] > 0
    assert 0 <= result["playability_score"] <= 100
    assert 0 <= result["difficulty_score"] <= 100
    assert result["time_estimate_seconds"] > 0
    assert result["heatmap"]["type"] == "grid"
    assert len(result["heatmap"]["data"]) == 10


def test_analyze_level_russian():
    result = analyze_level(SAMPLE, lang="ru")
    assert result["lang"] == "ru"
    assert "Проходимость" in result["summary"] or "проходимость" in result["summary"].lower()


def test_analyze_blocked_level():
    blocked = {
        "level_name": "Blocked",
        "width": 5,
        "height": 5,
        "tiles": [
            list("WWWWW"),
            list("W S W"),
            list("WWWWW"),
            list("W E W"),
            list("WWWWW"),
        ],
        "entities": [
            {"type": "start", "x": 2, "y": 1},
            {"type": "end", "x": 2, "y": 3},
        ],
    }
    # Fix tiles - S and E are walkable letters that aren't walls; use spaces
    blocked["tiles"] = [
        list("WWWWW"),
        list("W   W"),
        list("WWWWW"),
        list("W   W"),
        list("WWWWW"),
    ]
    result = analyze_level(blocked, lang="en")
    assert result["analysis"]["path_exists"] is False
    assert any(i["type"] == "no_path" for i in result["issues"])


def test_compare_levels():
    other = dict(SAMPLE)
    other["level_name"] = "Harder"
    other["entities"] = list(SAMPLE["entities"]) + [
        {"type": "enemy", "x": 2, "y": 2, "name": "Boss", "health": 200, "damage": 40}
    ]
    cmp = compare_levels(SAMPLE, other, lang="en")
    assert "delta" in cmp
    assert "playability" in cmp["delta"]


@pytest.mark.asyncio
async def test_level_analyzer_api(client: AsyncClient):
    email = "level_analyzer@example.com"
    password = "password1234"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "LA"},
    )
    assert reg.status_code == 201, reg.text
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200

    res = await client.post("/api/v1/level-analyzer", json={**SAMPLE, "lang": "en"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["tool"] == "level_analyzer"
    assert body["status"] == "completed"
    assert "playability_score" in body["output_data"]

    cmp = await client.post(
        "/api/v1/level-analyzer/compare",
        json={"level_a": SAMPLE, "level_b": SAMPLE, "lang": "en"},
    )
    assert cmp.status_code == 200, cmp.text
    assert "delta" in cmp.json()
