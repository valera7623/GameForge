"""Tests for AI Playtest Analyzer."""

from __future__ import annotations

import re

import pytest
from httpx import AsyncClient

from app.services.ai_playtest_analyzer import analyze_playtest

SAMPLE = {
    "game_name": "Dungeon Explorer",
    "lang": "en",
    "sessions": [
        {
            "session_id": "sess_001",
            "player_id": "player_001",
            "duration_seconds": 1200,
            "deaths": 3,
            "completion_time": 1080,
            "feedback": {
                "rating": 4,
                "comment": "Great game! The combat feels smooth, but the tutorial was confusing.",
                "tags": ["combat", "tutorial", "confusing"],
            },
            "events": [
                {"type": "start", "timestamp": 0},
                {"type": "combat", "timestamp": 100, "duration": 45},
                {"type": "death", "timestamp": 145},
                {"type": "respawn", "timestamp": 150},
                {"type": "combat", "timestamp": 200, "duration": 30},
                {"type": "death", "timestamp": 230},
                {"type": "respawn", "timestamp": 235},
                {"type": "treasure", "timestamp": 360},
                {"type": "boss", "timestamp": 500, "duration": 120, "name": "Boss 2"},
                {"type": "death", "timestamp": 560},
                {"type": "complete", "timestamp": 620},
            ],
        },
        {
            "session_id": "sess_002",
            "player_id": "player_002",
            "duration_seconds": 1800,
            "deaths": 8,
            "completion_time": None,
            "feedback": {
                "rating": 2,
                "comment": "Way too hard! The second boss is impossible. I gave up after 20 tries.",
                "tags": ["difficulty", "boss", "frustrating"],
            },
            "events": [
                {"type": "start", "timestamp": 0},
                {"type": "combat", "timestamp": 100, "duration": 30},
                {"type": "death", "timestamp": 130},
                {"type": "boss", "timestamp": 280, "name": "Boss 2"},
                {"type": "death", "timestamp": 300},
                {"type": "death", "timestamp": 310},
                {"type": "quit", "timestamp": 330},
            ],
        },
    ],
}


def test_analyze_playtest_en():
    result = analyze_playtest(SAMPLE, lang="en")
    assert result["summary"]["total_sessions"] == 2
    assert result["summary"]["completion_rate"] == 50.0
    assert result["health_score"] >= 0
    assert result["insights"] or result["issues"]
    assert result["recommendations"]
    assert any(v["type"] == "bar_chart" for v in result["visualizations"])
    assert any(v["type"] == "heatmap" for v in result["visualizations"])


def test_analyze_playtest_ru():
    data = dict(SAMPLE)
    data["lang"] = "ru"
    result = analyze_playtest(data, lang="ru")
    assert result["lang"] == "ru"
    assert re.search(r"[А-Яа-яЁё]", result["summary_text"])
    assert re.search(r"[А-Яа-яЁё]", result["methodology"])


@pytest.mark.asyncio
async def test_playtest_analyzer_api(client: AsyncClient):
    email = "playtest_analyzer@example.com"
    password = "password1234"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "PTA"},
    )
    assert reg.status_code == 201, reg.text
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200

    res = await client.post("/api/v1/playtest-analyzer", json=SAMPLE)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["tool"] == "playtest_analyzer"
    assert body["status"] == "completed"
    assert body["output_data"]["summary"]["total_sessions"] == 2
