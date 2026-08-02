"""AI Quest Generator — quests, dialogues, rewards."""

from __future__ import annotations

import json
import random
from typing import Any

from app.config import get_settings

settings = get_settings()


def _mock_quest(setting: str, quest_type: str, length: str, tone: str) -> dict[str, Any]:
    rng = random.Random(hash(f"{setting}{quest_type}{length}") & 0xFFFFFFFF)
    titles = [
        f"Shadows over {setting.split()[0].title()}",
        f"The Lost Relic of {setting[:20].title()}",
        f"Whispers in {setting[:15].title()}",
        f"Call of the {tone.title()} Path",
    ]
    objectives_pool = [
        {"id": "obj_1", "text": "Speak with the village elder", "type": "talk"},
        {"id": "obj_2", "text": "Investigate the ruined shrine", "type": "explore"},
        {"id": "obj_3", "text": "Defeat the guardian", "type": "combat"},
        {"id": "obj_4", "text": "Retrieve the ancient artifact", "type": "collect"},
        {"id": "obj_5", "text": "Return to the quest giver", "type": "return"},
        {"id": "obj_6", "text": "Escort the merchant safely", "type": "escort"},
        {"id": "obj_7", "text": "Solve the temple puzzle", "type": "puzzle"},
    ]
    n = {"short": 3, "medium": 4, "long": 6}.get(length, 4)
    objectives = objectives_pool[:n]

    dialogues = [
        {
            "npc": "Quest Giver",
            "lines": [
                {"speaker": "npc", "text": f"Traveler, darkness stirs in {setting}."},
                {"speaker": "player", "text": "What must I do?"},
                {
                    "speaker": "npc",
                    "text": f"Complete this {quest_type} quest — the fate of many depends on it.",
                },
            ],
        },
        {
            "npc": "Guardian",
            "lines": [
                {"speaker": "npc", "text": "None shall pass without proving their worth!"},
                {"speaker": "player", "text": "Then face me!"},
            ],
        },
        {
            "npc": "Quest Giver",
            "lines": [
                {"speaker": "npc", "text": "You return victorious. Take this reward, hero."},
                {"speaker": "player", "text": "Glad I could help."},
            ],
        },
    ]

    rewards = {
        "xp": rng.randint(100, 500) * n,
        "gold": rng.randint(50, 300) * n,
        "items": [
            {"id": "reward_weapon", "name": f"{tone.title()} Blade", "rarity": "rare"},
            {"id": "reward_consumable", "name": "Elixir of Vigor", "rarity": "common"},
        ],
    }

    return {
        "title": rng.choice(titles),
        "quest_type": quest_type,
        "setting": setting,
        "length": length,
        "tone": tone,
        "description": (
            f"A {quest_type} quest set in {setting}. "
            f"The player must navigate challenges in a {tone} atmosphere "
            f"across {n} objectives."
        ),
        "objectives": objectives,
        "dialogues": dialogues,
        "rewards": rewards,
        "branching": {
            "optional_path": "Help the wounded scout for bonus XP",
            "failure_state": "If the guardian wins, the shrine collapses",
        },
        "export": {
            "unity": "ScriptableObject / QuestData asset",
            "unreal": "DataAsset for QuestFramework",
            "godot": "Resource (.tres) for QuestManager",
        },
    }


async def generate_quest(
    setting: str, quest_type: str = "side", length: str = "medium", tone: str = "adventure"
) -> dict[str, Any]:
    if settings.USE_MOCK_AI:
        return _mock_quest(setting, quest_type, length, tone)
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required when USE_MOCK_AI=false")
    return await _openai_quest(setting, quest_type, length, tone)


async def _openai_quest(setting: str, quest_type: str, length: str, tone: str) -> dict[str, Any]:
    from app.services.openai_client import get_openai_client

    client = get_openai_client()
    prompt = f"""Create a game quest as JSON only.
Setting: {setting}, type: {quest_type}, length: {length}, tone: {tone}
Include: title, description, objectives[], dialogues[], rewards, branching, export hints.
Respond with valid JSON only."""

    resp = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)
