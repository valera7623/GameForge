"""AI Level Designer — generates tilemap JSON from text description."""

from __future__ import annotations

import json
import random
import re
from typing import Any

from app.config import get_settings

settings = get_settings()

TILE = {"empty": 0, "wall": 1, "floor": 2, "door": 3, "trap": 4, "water": 5, "chest": 6}

LEVEL_STYLES = ("dungeon", "cave", "temple", "city", "winter", "sci_fi", "desert")
LEVEL_DIFFICULTIES = ("easy", "medium", "hard")

_DIFFICULTY = {
    "easy": {"enemy_mult": 0.45, "trap_mult": 0.35, "chest_mult": 1.4, "enemy_hp": (15, 40)},
    "medium": {"enemy_mult": 1.0, "trap_mult": 1.0, "chest_mult": 1.0, "enemy_hp": (20, 80)},
    "hard": {"enemy_mult": 1.75, "trap_mult": 2.0, "chest_mult": 0.65, "enemy_hp": (40, 120)},
}

_STYLE_ENEMIES = {
    "dungeon": ["skeleton", "slime", "bat"],
    "cave": ["bat", "slime", "spider"],
    "temple": ["skeleton", "mummy", "guardian"],
    "city": ["thug", "guard", "rat"],
    "winter": ["wolf", "ice_slime", "yeti"],
    "sci_fi": ["drone", "android", "slime"],
    "desert": ["scorpion", "bandit", "snake"],
}


def _title_from_desc(description: str) -> str:
    words = re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", description)
    return " ".join(w.capitalize() for w in words[:5]) or "Generated Level"


def _normalize_style(style: str) -> str:
    s = (style or "dungeon").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {"scifi": "sci_fi", "sci-fi": "sci_fi", "science_fiction": "sci_fi"}
    s = aliases.get(s, s)
    return s if s in LEVEL_STYLES else "dungeon"


def _normalize_difficulty(difficulty: str) -> str:
    d = (difficulty or "medium").strip().lower()
    return d if d in LEVEL_DIFFICULTIES else "medium"


def _carve_rooms(rng: random.Random, grid: list[list[int]], width: int, height: int, count: int) -> list[tuple[int, int, int, int]]:
    rooms: list[tuple[int, int, int, int]] = []
    for _ in range(count):
        rw, rh = rng.randint(4, 8), rng.randint(4, 8)
        rx = rng.randint(1, max(1, width - rw - 1))
        ry = rng.randint(1, max(1, height - rh - 1))
        for y in range(ry, min(ry + rh, height - 1)):
            for x in range(rx, min(rx + rw, width - 1)):
                grid[y][x] = TILE["floor"]
        rooms.append((rx, ry, rw, rh))
    return rooms


def _carve_corridors(grid: list[list[int]], rooms: list[tuple[int, int, int, int]], width: int, height: int) -> None:
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


def _carve_city_grid(rng: random.Random, grid: list[list[int]], width: int, height: int) -> list[tuple[int, int, int, int]]:
    """Orthogonal streets + building blocks."""
    rooms: list[tuple[int, int, int, int]] = []
    step = max(4, min(width, height) // 6)
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if x % step == 0 or y % step == 0:
                grid[y][x] = TILE["floor"]
    for by in range(2, height - 3, step):
        for bx in range(2, width - 3, step):
            bw, bh = rng.randint(2, max(2, step - 2)), rng.randint(2, max(2, step - 2))
            for y in range(by, min(by + bh, height - 1)):
                for x in range(bx, min(bx + bw, width - 1)):
                    if grid[y][x] != TILE["floor"]:
                        grid[y][x] = TILE["floor"]
            rooms.append((bx, by, bw, bh))
    if not rooms:
        rooms = _carve_rooms(rng, grid, width, height, 4)
        _carve_corridors(grid, rooms, width, height)
    return rooms


def _carve_cave(rng: random.Random, grid: list[list[int]], width: int, height: int) -> list[tuple[int, int, int, int]]:
    """Irregular blobs instead of rectangles."""
    rooms: list[tuple[int, int, int, int]] = []
    for _ in range(rng.randint(5, 9)):
        cx, cy = rng.randint(3, width - 4), rng.randint(3, height - 4)
        rad = rng.randint(2, 5)
        minx = max(1, cx - rad)
        maxx = min(width - 2, cx + rad)
        miny = max(1, cy - rad)
        maxy = min(height - 2, cy + rad)
        for y in range(miny, maxy + 1):
            for x in range(minx, maxx + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= rad * rad + rng.randint(-1, 2):
                    grid[y][x] = TILE["floor"]
        rooms.append((minx, miny, max(1, maxx - minx + 1), max(1, maxy - miny + 1)))
    _carve_corridors(grid, rooms, width, height)
    return rooms


def _apply_style_flavor(
    rng: random.Random,
    grid: list[list[int]],
    width: int,
    height: int,
    style: str,
    description: str,
    trap_count: int,
) -> None:
    desc = description.lower()
    water_budget = width * height // 22
    if style in ("temple", "winter", "cave") or any(k in desc for k in ("water", "underwater", "ice", "lake")):
        tile = TILE["water"]
        n = water_budget if style != "desert" else water_budget // 4
        for _ in range(max(0, n)):
            x, y = rng.randint(1, width - 2), rng.randint(1, height - 2)
            if grid[y][x] == TILE["floor"]:
                grid[y][x] = tile
    if style == "desert":
        # Sparse open floor already; sprinkle traps as dunes hazards
        pass
    if style == "sci_fi":
        for _ in range(rng.randint(2, 6)):
            x, y = rng.randint(1, width - 2), rng.randint(1, height - 2)
            if grid[y][x] == TILE["floor"]:
                grid[y][x] = TILE["door"]
    for _ in range(max(0, trap_count)):
        x, y = rng.randint(1, width - 2), rng.randint(1, height - 2)
        if grid[y][x] == TILE["floor"]:
            grid[y][x] = TILE["trap"]


def _mock_level(
    description: str,
    width: int,
    height: int,
    style: str,
    difficulty: str = "medium",
) -> dict[str, Any]:
    style = _normalize_style(style)
    difficulty = _normalize_difficulty(difficulty)
    cfg = _DIFFICULTY[difficulty]
    rng = random.Random((hash(description) ^ hash(style) ^ hash(difficulty)) & 0xFFFFFFFF)
    grid = [[TILE["wall"] for _ in range(width)] for _ in range(height)]

    if style == "city":
        rooms = _carve_city_grid(rng, grid, width, height)
    elif style == "cave":
        rooms = _carve_cave(rng, grid, width, height)
    elif style == "desert":
        rooms = _carve_rooms(rng, grid, width, height, rng.randint(3, 5))
        _carve_corridors(grid, rooms, width, height)
    else:
        rooms = _carve_rooms(rng, grid, width, height, rng.randint(4, 8))
        _carve_corridors(grid, rooms, width, height)

    base_traps = rng.randint(3, 8)
    if "trap" in description.lower():
        base_traps += 3
    trap_count = max(0, int(round(base_traps * cfg["trap_mult"])))
    _apply_style_flavor(rng, grid, width, height, style, description, trap_count)

    enemy_types = list(_STYLE_ENEMIES.get(style, _STYLE_ENEMIES["dungeon"]))
    desc = description.lower()
    if "dragon" in desc:
        enemy_types.append("dragon")
    base_enemies = rng.randint(3, 10)
    enemy_count = max(1, int(round(base_enemies * cfg["enemy_mult"])))
    enemies = []
    for _ in range(enemy_count):
        if not rooms:
            break
        rx, ry, rw, rh = rooms[rng.randint(0, len(rooms) - 1)]
        enemies.append(
            {
                "type": rng.choice(enemy_types),
                "x": rx + rng.randint(0, max(0, rw - 1)),
                "y": ry + rng.randint(0, max(0, rh - 1)),
                "hp": rng.randint(*cfg["enemy_hp"]),
            }
        )

    base_chests = rng.randint(2, 6)
    chest_count = max(1, int(round(base_chests * cfg["chest_mult"])))
    items = []
    for _ in range(chest_count):
        if not rooms:
            break
        rx, ry, rw, rh = rooms[rng.randint(0, len(rooms) - 1)]
        ix = rx + rng.randint(0, max(0, rw - 1))
        iy = ry + rng.randint(0, max(0, rh - 1))
        if 0 <= iy < height and 0 <= ix < width:
            grid[iy][ix] = TILE["chest"]
            items.append(
                {
                    "type": rng.choice(["health_potion", "gold", "key", "weapon"]),
                    "x": ix,
                    "y": iy,
                }
            )

    spawn = None
    exit_pos = None
    if rooms:
        spawn = {"x": rooms[0][0] + 1, "y": rooms[0][1] + 1}
        spawn["x"] = min(max(1, spawn["x"]), width - 2)
        spawn["y"] = min(max(1, spawn["y"]), height - 2)
        last = rooms[-1]
        exit_pos = {"x": last[0] + last[2] // 2, "y": last[1] + last[3] // 2}
        if exit_pos and 0 <= exit_pos["y"] < height and 0 <= exit_pos["x"] < width:
            grid[exit_pos["y"]][exit_pos["x"]] = TILE["door"]

    return {
        "name": _title_from_desc(description),
        "description": description,
        "style": style,
        "difficulty": difficulty,
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
            "godot": "Load JSON into TileMap / custom Resource",
        },
    }


async def generate_level(
    description: str,
    width: int = 32,
    height: int = 32,
    style: str = "dungeon",
    difficulty: str = "medium",
) -> dict[str, Any]:
    style = _normalize_style(style)
    difficulty = _normalize_difficulty(difficulty)
    if settings.USE_MOCK_AI:
        return _mock_level(description, width, height, style, difficulty)
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required when USE_MOCK_AI=false")
    return await _openai_level(description, width, height, style, difficulty)


async def _openai_level(
    description: str, width: int, height: int, style: str, difficulty: str
) -> dict[str, Any]:
    from app.services.openai_client import chat_completion

    density = {
        "easy": "few enemies and traps, more treasure",
        "medium": "balanced enemies, traps, and treasure",
        "hard": "many enemies and traps, scarce treasure",
    }[difficulty]
    prompt = f"""Generate a game level as JSON only (no markdown).
Description: {description}
Size: {width}x{height}
Style: {style} (one of: {", ".join(LEVEL_STYLES)})
Difficulty: {difficulty} — {density}
Schema: {{
  "name": str, "description": str, "style": str, "difficulty": str,
  "width": int, "height": int,
  "tiles": int[][] (0 empty, 1 wall, 2 floor, 3 door, 4 trap, 5 water, 6 chest),
  "tile_legend": dict, "enemies": [{{"type","x","y","hp"}}],
  "items": [{{"type","x","y"}}], "spawn": {{"x","y"}}, "exit": {{"x","y"}},
  "rooms": [{{"x","y","w","h"}}]
}}
Match the style visually in layout (cave=organic, city=grid streets, desert=sparse, winter=water as ice, sci_fi=hatches/doors).
Keep tiles as a compact {height}x{width} grid. Respond with valid JSON only."""

    resp = await chat_completion(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content)
    data.setdefault("tile_legend", TILE)
    data["style"] = _normalize_style(data.get("style") or style)
    data["difficulty"] = _normalize_difficulty(data.get("difficulty") or difficulty)
    return data
