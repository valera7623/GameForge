"""Tests for AI Review Analyzer."""

from __future__ import annotations

import re

import pytest
from httpx import AsyncClient

from app.services.ai_review_analyzer import analyze_reviews

SAMPLE = {
    "game_name": "Dungeon Explorer",
    "source": "steam",
    "lang": "en",
    "reviews": [
        {
            "review_id": "rev_001",
            "rating": 5,
            "text": (
                "Amazing game! The combat is smooth and the dungeons are procedurally generated "
                "perfectly. I've played for 50 hours and still finding new things. Highly recommend!"
            ),
            "date": "2026-08-01",
            "language": "en",
        },
        {
            "review_id": "rev_002",
            "rating": 2,
            "text": "Too hard. The second boss is completely unfair. I died 20 times and gave up. The tutorial is also confusing.",
            "date": "2026-08-02",
            "language": "en",
        },
        {
            "review_id": "rev_003",
            "rating": 4,
            "text": "Great concept, but the inventory UI is a mess. I can't find what I'm looking for. Also, some enemies are way too strong for early levels.",
            "date": "2026-08-03",
            "language": "en",
        },
        {
            "review_id": "rev_004",
            "rating": 3,
            "text": "Игра неплохая, но босс 2 слишком сложный. Много багов в инвентаре. В целом играть можно.",
            "date": "2026-08-04",
            "language": "ru",
        },
    ],
}


def test_analyze_reviews_en():
    result = analyze_reviews(SAMPLE, lang="en")
    assert result["summary"]["total_reviews"] == 4
    assert result["summary"]["average_rating"] > 0
    assert result["sentiments"]["positive"] + result["sentiments"]["negative"] + result["sentiments"]["neutral"] == 100.0 or abs(
        result["sentiments"]["positive"] + result["sentiments"]["negative"] + result["sentiments"]["neutral"] - 100.0
    ) < 0.2
    assert result["top_issues"] or result["categories"]
    assert result["recommendations"]
    assert any(v["type"] == "bar_chart" for v in result["visualizations"])


def test_analyze_reviews_ru():
    data = dict(SAMPLE)
    data["lang"] = "ru"
    result = analyze_reviews(data, lang="ru")
    assert result["lang"] == "ru"
    assert re.search(r"[А-Яа-яЁё]", result["summary_text"])
    assert re.search(r"[А-Яа-яЁё]", result["methodology"])


@pytest.mark.asyncio
async def test_review_analyzer_api(client: AsyncClient):
    email = "review_analyzer@example.com"
    password = "password1234"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "RA"},
    )
    assert reg.status_code == 201, reg.text
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200

    res = await client.post("/api/v1/review-analyzer", json=SAMPLE)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["tool"] == "review_analyzer"
    assert body["status"] == "completed"
    assert body["output_data"]["summary"]["total_reviews"] == 4
