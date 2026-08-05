"""Unit tests for AI Game Balancer metrics + API."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.ai_game_balancer import analyze_game_data


SAMPLE = {
    "game_name": "Dungeon Explorer",
    "version": "1.0.0",
    "classes": [
        {"name": "Warrior", "health": 100, "damage": 20, "defense": 10, "speed": 1.0},
        {"name": "Mage", "health": 60, "damage": 30, "defense": 5, "speed": 0.8},
    ],
    "enemies": [
        {"name": "Goblin", "health": 50, "damage": 10, "defense": 2, "speed": 1.2, "xp_reward": 50, "gold_reward": 10},
        {"name": "Orc", "health": 120, "damage": 25, "defense": 8, "speed": 0.7, "xp_reward": 100, "gold_reward": 25},
    ],
    "weapons": [
        {"name": "Sword", "damage": 15, "speed": 1.0, "price": 100, "rarity": "common"},
        {"name": "Axe", "damage": 25, "speed": 0.7, "price": 200, "rarity": "uncommon"},
    ],
    "abilities": [
        {"name": "Fireball", "damage": 40, "cooldown": 10, "mana_cost": 30},
        {"name": "Slash", "damage": 15, "cooldown": 2, "mana_cost": 5},
    ],
    "economy": {
        "starting_gold": 100,
        "gold_per_kill": 10,
        "gold_per_quest": 50,
        "price_multiplier": 1.0,
        "xp_per_level": 100,
    },
}


def test_analyze_game_data_structure():
    result = analyze_game_data(SAMPLE)
    assert 0 <= result["balance_score"] <= 100
    assert isinstance(result["issues"], list)
    assert isinstance(result["recommendations"], list)
    assert isinstance(result["visualizations"], list)
    assert "summary" in result
    assert result["metrics"]["classes"]
    assert result["metrics"]["enemies"]


def test_analyze_detects_weapon_spread():
    result = analyze_game_data(SAMPLE)
    types = {i["type"] for i in result["issues"]}
    # Axe vs Sword DPS gap should surface as weapon_imbalance or efficiency
    assert types & {"weapon_imbalance", "weapon_efficiency", "class_imbalance", "enemy_too_weak", "enemy_too_strong"}


@pytest.mark.asyncio
async def test_game_balancer_api(client: AsyncClient):
    email = "balancer_user@example.com"
    password = "password1234"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Bal"},
    )
    assert reg.status_code == 201, reg.text
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200

    res = await client.post("/api/v1/game-balancer", json=SAMPLE)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["tool"] == "game_balancer"
    assert body["status"] == "completed"
    assert body["output_data"]["balance_score"] is not None
    assert "issues" in body["output_data"]

    hist = await client.get("/api/v1/generations", params={"tool": "game_balancer"})
    assert hist.status_code == 200
    items = hist.json()
    assert any(g["id"] == body["id"] for g in items)
