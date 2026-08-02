"""AI Level Designer — generates tilemap JSON from text description."""

from __future__ import annotations

import json
import random
import re
from typing import Any

from app.config import get_settings

settings = get_settings()

TILE = {"empty": 0, "wall": 1, "floor": 2, "door": 3, "trap": 4, "water": 5, "chest": 6}


def _mock_level(description: str, width: int, height: int, style: str) -> dict[str, Any]:
    rng = random.Random(hash(description) & 0xFFFFFFFF)
    grid = [[TILE["wall"] for _ in range(width)] for _ in range(height)]

    # Carve rooms
    rooms: list[tuple[int, int, int, int]] = []
    for _ in range(rng.randint(4, 8)):
        rw, rh = rng.randint(4, 8), rng.randint(4, 8)
        rx = rng.randint(1, max(1, width - rw - 1))
        ry = rng.randint(1, max(1, height - rh - 1))
        for y in range(ry, min(ry + rh, height - 1)):
            for x in range(rx, min(rx + rw, width - 1)):
                grid[y][x] = TILE["floor"]
        rooms.append((rx, ry, rw, rh))

    # Corridors between room centers
    for i in range(len(rooms) - 1):
        x1 = rooms[i][0] + rooms[i][2] // 2
        y1 = rooms[i][1] + rooms[i][3] // 2
        x2 = rooms[i + 1][0] + rooms[i + 1][2] // 2
        y2 = rooms[i + 1][1] + rooms[i + 1][3] // 2
        for x in range(min(x1, x2), max(x1, x2) + 1):
            if 0 < x < width - 1 and 0 < y1 < height - 1:
                grid[y1][x] = TILE["floor"]
        for y in range(min(y1, y2), max(y1, y2) + 1):
            if 0 < x2 < width - 1 and 0 < y < height - 1:
                grid[y][x2] = TILE["floor"]

    # Flavor tiles from description keywords
    desc = description.lower()
    if "water" in desc or "underwater" in desc or "temple" in desc:
        for _ in range(width * height // 20):
            x, y = rng.randint(1, width - 2), rng.randint(1, height - 2)
            if grid[y][x] == TILE["floor"]:
                grid[y][x] = TILE["water"]
    if "trap" in desc:
        for _ in range(rng.randint(3, 8)):
            x, y = rng.randint(1, width - 2), rng.randint(1, height - 2)
            if grid[y][x] == TILE["floor"]:
                grid[y][x] = TILE["trap"]

    enemies = []
    enemy_types = ["skeleton", "slime", "bat"]
    if "dragon" in desc:
        enemy_types.append("dragon")
    if "skeleton" in desc:
        enemy_types = ["skeleton", "skeleton_archer"]
    for _ in range(rng.randint(3, 10)):
        if not rooms:
            break
        rx, ry, rw, rh = rooms[rng.randint(0, len(rooms) - 1)]
        enemies.append(
            {
                "type": rng.choice(enemy_types),
                "x": rx + rng.randint(1, max(1, rw - 2)),
                "y": ry + rng.randint(1, max(1, rh - 2)),
                "hp": rng.randint(20, 80),
            }
        )

    items = []
    for _ in range(rng.randint(2, 6)):
        if not rooms:
            break
        rx, ry, rw, rh = rooms[rng.randint(0, len(rooms) - 1)]
        ix, iy = rx + rng.randint(1, max(1, rw - 2)), ry + rng.randint(1, max(1, rh - 2))
        grid[iy][ix] = TILE["chest"]
        items.append({"type": rng.choice(["health_potion", "gold", "key", "weapon"]), "x": ix, "y": iy})

    spawn = None
    exit_pos = None
    if rooms:
        spawn = {"x": rooms[0][0] + 1, "y": rooms[0][1] + 1}
        last = rooms[-1]
        exit_pos = {"x": last[0] + last[2] // 2, "y": last[1] + last[3] // 2}
        if exit_pos:
            grid[exit_pos["y"]][exit_pos["x"]] = TILE["door"]

    return {
        "name": _title_from_desc(description),
        "description": description,
        "style": style,
        "width": width,
        "height": height,
        "tiles": grid,
        "tile_legend": TILE,
        "enemies": enemies,
        "items": items,
        "spawn": spawn,
        "exit": exit_pos,
        "rooms": [{"x": r[0], "y": r[1], "w": r[2], "h": r[3]} for r in rooms],
        "engine_hints": {
            "unity": "Import as Tilemap via LevelImporter.cs",
            "unreal": "Use as DataTable for ProceduralDungeon",
        },
    }


def _title_from_desc(description: str) -> str:
    words = re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", description)
    return " ".join(w.capitalize() for w in words[:5]) or "Generated Level"


async def generate_level(
    description: str, width: int = 32, height: int = 32, style: str = "dungeon"
) -> dict[str, Any]:
    if settings.OPENAI_API_KEY and not settings.USE_MOCK_AI:
        try:
            return await _openai_level(description, width, height, style)
        except Exception:
            pass
    return _mock_level(description, width, height, style)


async def _openai_level(description: str, width: int, height: int, style: str) -> dict[str, Any]:
    from app.services.openai_client import get_openai_client

    client = get_openai_client()
    prompt = f"""Generate a game level as JSON only (no markdown).
Description: {description}
Size: {width}x{height}, style: {style}
Schema: {{
  "name": str, "description": str, "style": str, "width": int, "height": int,
  "tiles": int[][] (0 empty, 1 wall, 2 floor, 3 door, 4 trap, 5 water, 6 chest),
  "tile_legend": dict, "enemies": [{{"type","x","y","hp"}}],
  "items": [{{"type","x","y"}}], "spawn": {{"x","y"}}, "exit": {{"x","y"}},
  "rooms": [{{"x","y","w","h"}}]
}}
Keep tiles as a compact {height}x{width} grid. Respond with valid JSON only."""

    resp = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content)
    data.setdefault("tile_legend", TILE)
    return data
