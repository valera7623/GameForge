"""AI Level Analyzer — pathfinding, difficulty, density, heatmap."""

from __future__ import annotations

import json
import math
from collections import deque
from typing import Any

from app.config import get_settings

settings = get_settings()

SEVERITY_WEIGHT = {"high": 12, "medium": 7, "low": 3}
WALL_CHARS = {"W", "#", "X", "WALL"}
FLOOR_CHARS = {" ", ".", "F", "FLOOR", "0"}

_MSG: dict[str, dict[str, str]] = {
    "en": {
        "no_path": "No path from start to end — level is not completable",
        "open_path": "Ensure a walkable path from start {start} to end {end}",
        "dead_end": "Dead end at ({x}, {y}) without rewards",
        "remove_dead_end": "Open dead end at ({x}, {y}) by adding a connection to the main path",
        "empty_room": "Empty room/zone around ({x}, {y}) with no enemies or rewards",
        "add_reward": "Add treasure or encounter near ({x}, {y})",
        "enemy_imbalance": "{name} at ({x},{y}) is too strong for this stage of the level",
        "reduce_power": "Reduce {name} health from {old} to {new}",
        "too_many_enemies": "Enemy density {density} is high (target 0.1–0.3)",
        "too_few_enemies": "Enemy density {density} is low (target 0.1–0.3)",
        "too_many_traps": "Trap density {density} is high (target 0.02–0.08)",
        "too_few_treasures": "Treasure density {density} is low (target 0.05–0.15)",
        "too_many_treasures": "Treasure density {density} is high (target 0.05–0.15)",
        "time_over_limit": "Estimated clear time {est}s exceeds time limit {limit}s",
        "extend_limit": "Increase time_limit from {old} to {new} or shorten the path",
        "path_too_short": "Main path is only {length} steps — may feel too short",
        "path_too_long": "Main path is {length} steps — may feel too long",
        "heatmap_low": "Low activity",
        "heatmap_mid": "Medium activity",
        "heatmap_high": "High activity",
        "summary": (
            "Overall playability: {play}/100. Difficulty: {diff}/100. "
            "Estimated time: {time}s. "
        ),
        "summary_issues": "Main issues: {issues}. ",
        "summary_ok": "No major layout issues detected. ",
        "summary_fix": "Top fix: {fix}.",
        "summary_keep": "Ready for playtesting.",
        "methodology": "BFS pathfinding + density/difficulty heuristics",
        "methodology_llm": "Pathfinding heuristics + GPT narrative polish",
        "untitled": "Untitled Level",
        "enemy_default": "Enemy",
        "layout": "layout",
        "enemy": "enemy",
        "treasure": "treasure",
        "timing": "timing",
    },
    "ru": {
        "no_path": "Нет пути от старта до финиша — уровень непроходим",
        "open_path": "Обеспечьте проходимый путь от старта {start} до финиша {end}",
        "dead_end": "Тупик в ({x}, {y}) без наград",
        "remove_dead_end": "Откройте тупик ({x}, {y}), соединив его с основным путём",
        "empty_room": "Пустая зона около ({x}, {y}) — нет врагов и наград",
        "add_reward": "Добавьте сокровище или энкаунтер около ({x}, {y})",
        "enemy_imbalance": "{name} в ({x},{y}) слишком силён для этой части уровня",
        "reduce_power": "Снизить здоровье {name}: {old} → {new}",
        "too_many_enemies": "Плотность врагов {density} высокая (цель 0.1–0.3)",
        "too_few_enemies": "Плотность врагов {density} низкая (цель 0.1–0.3)",
        "too_many_traps": "Плотность ловушек {density} высокая (цель 0.02–0.08)",
        "too_few_treasures": "Плотность сокровищ {density} низкая (цель 0.05–0.15)",
        "too_many_treasures": "Плотность сокровищ {density} высокая (цель 0.05–0.15)",
        "time_over_limit": "Оценка прохождения {est}с превышает лимит {limit}с",
        "extend_limit": "Увеличьте time_limit с {old} до {new} или укоротите путь",
        "path_too_short": "Основной путь всего {length} шагов — уровень может быть слишком коротким",
        "path_too_long": "Основной путь {length} шагов — может ощущаться слишком длинным",
        "heatmap_low": "Низкая активность",
        "heatmap_mid": "Средняя активность",
        "heatmap_high": "Высокая активность",
        "summary": (
            "Проходимость: {play}/100. Сложность: {diff}/100. "
            "Оценка времени: {time}с. "
        ),
        "summary_issues": "Главные проблемы: {issues}. ",
        "summary_ok": "Критических проблем раскладки не найдено. ",
        "summary_fix": "Приоритетный фикс: {fix}.",
        "summary_keep": "Готово к плейтесту.",
        "methodology": "BFS-поиск пути + эвристики плотности/сложности",
        "methodology_llm": "Эвристики пути + GPT-нарратив",
        "untitled": "Уровень без названия",
        "enemy_default": "Враг",
        "layout": "раскладка",
        "enemy": "враг",
        "treasure": "сокровище",
        "timing": "тайминг",
    },
}


def _norm_lang(lang: str | None) -> str:
    return "ru" if str(lang or "").lower().startswith("ru") else "en"


def _t(lang: str, key: str, **kwargs: Any) -> str:
    table = _MSG.get(_norm_lang(lang), _MSG["en"])
    template = table.get(key) or _MSG["en"].get(key) or key
    return template.format(**kwargs) if kwargs else template


def _is_wall(cell: Any) -> bool:
    s = str(cell) if cell is not None else " "
    if s.upper() in WALL_CHARS or s == "W":
        return True
    return False


def _walkable(cell: Any) -> bool:
    return not _is_wall(cell)


def _neighbors(x: int, y: int, w: int, h: int) -> list[tuple[int, int]]:
    out = []
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h:
            out.append((nx, ny))
    return out


def _bfs_path(
    tiles: list[list[Any]], start: tuple[int, int], end: tuple[int, int]
) -> list[tuple[int, int]] | None:
    h = len(tiles)
    w = len(tiles[0]) if h else 0
    if not w:
        return None
    sx, sy = start
    ex, ey = end
    if not (0 <= sx < w and 0 <= sy < h and 0 <= ex < w and 0 <= ey < h):
        return None
    if not _walkable(tiles[sy][sx]) or not _walkable(tiles[ey][ex]):
        return None
    q = deque([(sx, sy)])
    prev: dict[tuple[int, int], tuple[int, int] | None] = {(sx, sy): None}
    while q:
        x, y = q.popleft()
        if (x, y) == (ex, ey):
            path = []
            cur: tuple[int, int] | None = (ex, ey)
            while cur is not None:
                path.append(cur)
                cur = prev[cur]
            path.reverse()
            return path
        for nx, ny in _neighbors(x, y, w, h):
            if (nx, ny) in prev:
                continue
            if not _walkable(tiles[ny][nx]):
                continue
            prev[(nx, ny)] = (x, y)
            q.append((nx, ny))
    return None


def _flood_reachable(tiles: list[list[Any]], start: tuple[int, int]) -> set[tuple[int, int]]:
    h = len(tiles)
    w = len(tiles[0]) if h else 0
    if not w:
        return set()
    sx, sy = start
    if not (0 <= sx < w and 0 <= sy < h) or not _walkable(tiles[sy][sx]):
        return set()
    seen = {(sx, sy)}
    q = deque([(sx, sy)])
    while q:
        x, y = q.popleft()
        for nx, ny in _neighbors(x, y, w, h):
            if (nx, ny) in seen:
                continue
            if not _walkable(tiles[ny][nx]):
                continue
            seen.add((nx, ny))
            q.append((nx, ny))
    return seen


def _find_entity(entities: list[dict], etype: str) -> tuple[int, int] | None:
    for e in entities:
        if str(e.get("type", "")).lower() == etype:
            try:
                return int(e["x"]), int(e["y"])
            except (KeyError, TypeError, ValueError):
                continue
    return None


def _infer_start_end(
    tiles: list[list[Any]], entities: list[dict]
) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
    start = _find_entity(entities, "start")
    end = _find_entity(entities, "end") or _find_entity(entities, "exit") or _find_entity(entities, "goal")
    h = len(tiles)
    w = len(tiles[0]) if h else 0
    if start is None:
        for y in range(h):
            for x in range(w):
                if _walkable(tiles[y][x]):
                    start = (x, y)
                    break
            if start:
                break
    if end is None:
        for y in range(h - 1, -1, -1):
            for x in range(w - 1, -1, -1):
                if _walkable(tiles[y][x]) and (x, y) != start:
                    end = (x, y)
                    break
            if end:
                break
    return start, end


def _walkable_count(tiles: list[list[Any]]) -> int:
    return sum(1 for row in tiles for c in row if _walkable(c))


def _dead_ends(tiles: list[list[Any]], reachable: set[tuple[int, int]]) -> list[tuple[int, int]]:
    h = len(tiles)
    w = len(tiles[0]) if h else 0
    ends = []
    for x, y in reachable:
        walks = [
            (nx, ny)
            for nx, ny in _neighbors(x, y, w, h)
            if _walkable(tiles[ny][nx])
        ]
        if len(walks) == 1:
            ends.append((x, y))
    return ends


def _empty_zones(
    tiles: list[list[Any]],
    reachable: set[tuple[int, int]],
    occupied: set[tuple[int, int]],
    path_set: set[tuple[int, int]],
) -> list[tuple[int, int]]:
    """Find walkable cells far from path and content (proxy for empty rooms)."""
    empties = []
    for x, y in reachable:
        if (x, y) in occupied or (x, y) in path_set:
            continue
        near_content = any(
            (nx, ny) in occupied for nx, ny in _neighbors(x, y, len(tiles[0]), len(tiles))
        )
        near_path = any((nx, ny) in path_set for nx, ny in _neighbors(x, y, len(tiles[0]), len(tiles)))
        if not near_content and not near_path:
            empties.append((x, y))
    # Deduplicate by clustering — keep every 4th to avoid spam
    return empties[:: max(1, len(empties) // 5)][:5] if empties else []


def _build_heatmap(
    w: int,
    h: int,
    path: list[tuple[int, int]] | None,
    entities: list[dict],
    reachable: set[tuple[int, int]],
) -> list[list[float]]:
    grid = [[0.0 for _ in range(w)] for _ in range(h)]
    if path:
        plen = max(len(path), 1)
        for i, (x, y) in enumerate(path):
            # Higher near start/combat mid; still elevated along path
            t = i / plen
            grid[y][x] = max(grid[y][x], 0.45 + 0.4 * (1 - abs(t - 0.5) * 2))
            for nx, ny in _neighbors(x, y, w, h):
                grid[ny][nx] = max(grid[ny][nx], 0.25)
    for e in entities:
        try:
            x, y = int(e["x"]), int(e["y"])
        except (KeyError, TypeError, ValueError):
            continue
        if not (0 <= x < w and 0 <= y < h):
            continue
        et = str(e.get("type", "")).lower()
        boost = 0.9 if et == "enemy" else (0.7 if et == "trap" else (0.55 if et == "treasure" else 0.35))
        grid[y][x] = max(grid[y][x], boost)
        for nx, ny in _neighbors(x, y, w, h):
            grid[ny][nx] = max(grid[ny][nx], boost * 0.5)
    for x, y in reachable:
        if grid[y][x] == 0:
            grid[y][x] = 0.05
    # Round for JSON friendliness
    return [[round(min(1.0, v), 2) for v in row] for row in grid]


def analyze_level(level_data: dict[str, Any], lang: str | None = None) -> dict[str, Any]:
    lang = _norm_lang(lang or level_data.get("lang"))
    tiles = level_data.get("tiles") or []
    if not tiles or not isinstance(tiles, list):
        tiles = [[" "]]
    # Normalize ragged rows
    height = int(level_data.get("height") or len(tiles))
    width = int(level_data.get("width") or (len(tiles[0]) if tiles else 1))
    norm: list[list[Any]] = []
    for y in range(height):
        row = list(tiles[y]) if y < len(tiles) else []
        while len(row) < width:
            row.append("W")
        norm.append(row[:width])
    tiles = norm

    entities = [e for e in (level_data.get("entities") or []) if isinstance(e, dict)]
    time_limit = int(level_data.get("time_limit") or 0)

    start, end = _infer_start_end(tiles, entities)
    path = _bfs_path(tiles, start, end) if start and end else None
    reachable = _flood_reachable(tiles, start) if start else set()
    path_set = set(path or [])
    walkable = max(_walkable_count(tiles), 1)

    enemies = [e for e in entities if str(e.get("type", "")).lower() == "enemy"]
    treasures = [e for e in entities if str(e.get("type", "")).lower() in ("treasure", "loot", "reward")]
    traps = [e for e in entities if str(e.get("type", "")).lower() == "trap"]

    occupied: set[tuple[int, int]] = set()
    for e in entities:
        try:
            occupied.add((int(e["x"]), int(e["y"])))
        except (KeyError, TypeError, ValueError):
            pass

    enemy_density = round(len(enemies) / walkable, 3)
    treasure_density = round(len(treasures) / walkable, 3)
    trap_density = round(len(traps) / walkable, 3)
    path_length = len(path) - 1 if path and len(path) > 1 else (0 if path else -1)

    # Time estimate: ~1.2s per step + combat time
    combat_time = sum(max(float(e.get("health") or 30) / max(float(e.get("damage") or 10), 1) * 1.5, 3) for e in enemies)
    trap_time = len(traps) * 2
    move_time = max(path_length, 0) * 1.2
    time_estimate = int(round(move_time + combat_time + trap_time + 10))

    # Difficulty 0-100
    enemy_power = sum(float(e.get("health") or 40) + float(e.get("damage") or 10) * 2 for e in enemies)
    trap_power = sum(float(t.get("damage") or 15) for t in traps)
    treasure_value = sum(float(t.get("value") or 50) for t in treasures)
    raw_diff = (enemy_power * 0.35 + trap_power * 0.25 + max(path_length, 0) * 0.4) / max(math.sqrt(walkable), 1)
    difficulty_score = int(max(0, min(100, raw_diff * 1.8)))

    issues: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []

    if not path:
        issues.append(
            {
                "type": "no_path",
                "severity": "high",
                "description": _t(lang, "no_path"),
                "location": {"x": end[0], "y": end[1]} if end else None,
            }
        )
        recommendations.append(
            {
                "target": _t(lang, "layout"),
                "action": "open_path",
                "location": {"start": list(start) if start else None, "end": list(end) if end else None},
                "description": _t(lang, "open_path", start=start, end=end),
            }
        )

    dead = _dead_ends(tiles, reachable)
    treasure_cells = set()
    for t in treasures:
        try:
            treasure_cells.add((int(t["x"]), int(t["y"])))
        except (KeyError, TypeError, ValueError):
            pass
    for x, y in dead[:6]:
        if (x, y) in (start, end):
            continue
        if (x, y) in treasure_cells:
            continue
        # Only flag if not on main path (path dead-ends at end are fine)
        if path and (x, y) == path[-1]:
            continue
        issues.append(
            {
                "type": "dead_end",
                "severity": "medium",
                "description": _t(lang, "dead_end", x=x, y=y),
                "location": {"x": x, "y": y},
            }
        )
        recommendations.append(
            {
                "target": _t(lang, "layout"),
                "action": "remove_dead_end",
                "location": {"x": x, "y": y},
                "description": _t(lang, "remove_dead_end", x=x, y=y),
            }
        )

    for x, y in _empty_zones(tiles, reachable, occupied, path_set):
        issues.append(
            {
                "type": "empty_room",
                "severity": "low",
                "description": _t(lang, "empty_room", x=x, y=y),
                "location": {"x": x, "y": y},
            }
        )
        recommendations.append(
            {
                "target": _t(lang, "treasure"),
                "action": "add_reward",
                "location": {"x": x, "y": y},
                "description": _t(lang, "add_reward", x=x, y=y),
            }
        )

    # Enemy power vs progress along path
    path_index = {p: i for i, p in enumerate(path or [])}
    plen = max(len(path or [0]), 1)
    for e in enemies:
        try:
            x, y = int(e["x"]), int(e["y"])
        except (KeyError, TypeError, ValueError):
            continue
        hp = float(e.get("health") or 50)
        dmg = float(e.get("damage") or 10)
        power = hp + dmg * 2
        idx = path_index.get((x, y), plen // 2)
        progress = idx / plen
        expected = 35 + progress * 55
        if power > expected * 1.45:
            name = str(e.get("name") or _t(lang, "enemy_default"))
            new_hp = max(20, round(hp * 0.65))
            issues.append(
                {
                    "type": "enemy_imbalance",
                    "severity": "high",
                    "description": _t(lang, "enemy_imbalance", name=name, x=x, y=y),
                    "location": {"x": x, "y": y},
                    "details": {
                        "enemy_power": round(power, 1),
                        "expected_power": round(expected, 1),
                        "difference": round(power - expected, 1),
                    },
                }
            )
            recommendations.append(
                {
                    "target": _t(lang, "enemy"),
                    "action": "reduce_power",
                    "location": {"x": x, "y": y},
                    "description": _t(lang, "reduce_power", name=name, old=hp, new=new_hp),
                }
            )

    if enemy_density > 0.3:
        issues.append(
            {
                "type": "enemy_density_high",
                "severity": "medium",
                "description": _t(lang, "too_many_enemies", density=enemy_density),
            }
        )
    elif enemy_density < 0.05 and walkable > 20:
        issues.append(
            {
                "type": "enemy_density_low",
                "severity": "low",
                "description": _t(lang, "too_few_enemies", density=enemy_density),
            }
        )

    if trap_density > 0.08:
        issues.append(
            {
                "type": "trap_density_high",
                "severity": "medium",
                "description": _t(lang, "too_many_traps", density=trap_density),
            }
        )
    if treasure_density < 0.03 and walkable > 20:
        issues.append(
            {
                "type": "treasure_density_low",
                "severity": "low",
                "description": _t(lang, "too_few_treasures", density=treasure_density),
            }
        )
    elif treasure_density > 0.2:
        issues.append(
            {
                "type": "treasure_density_high",
                "severity": "low",
                "description": _t(lang, "too_many_treasures", density=treasure_density),
            }
        )

    if time_limit and time_estimate > time_limit * 1.1:
        issues.append(
            {
                "type": "time_over_limit",
                "severity": "high",
                "description": _t(lang, "time_over_limit", est=time_estimate, limit=time_limit),
            }
        )
        recommendations.append(
            {
                "target": _t(lang, "timing"),
                "action": "extend_limit",
                "description": _t(
                    lang, "extend_limit", old=time_limit, new=int(time_estimate * 1.15)
                ),
            }
        )

    if path_length >= 0:
        if path_length < 15 and walkable > 40:
            issues.append(
                {
                    "type": "path_too_short",
                    "severity": "low",
                    "description": _t(lang, "path_too_short", length=path_length),
                }
            )
        elif path_length > 80:
            issues.append(
                {
                    "type": "path_too_long",
                    "severity": "medium",
                    "description": _t(lang, "path_too_long", length=path_length),
                }
            )

    # Dedup recommendations
    seen: set[str] = set()
    uniq_recs = []
    for r in recommendations:
        key = f"{r.get('action')}:{r.get('location')}:{r.get('description')}"
        if key in seen:
            continue
        seen.add(key)
        uniq_recs.append(r)

    penalty = sum(SEVERITY_WEIGHT.get(i.get("severity", "low"), 3) for i in issues)
    if not path:
        penalty += 25
    playability_score = int(max(0, min(100, 100 - penalty)))

    heatmap = _build_heatmap(width, height, path, entities, reachable)

    level_name = str(level_data.get("level_name") or _t(lang, "untitled"))
    top = [i["description"] for i in issues[:3]]
    summary = _t(lang, "summary", play=playability_score, diff=difficulty_score, time=time_estimate)
    summary += _t(lang, "summary_issues", issues="; ".join(top)) if top else _t(lang, "summary_ok")
    summary += (
        _t(lang, "summary_fix", fix=uniq_recs[0]["description"]) if uniq_recs else _t(lang, "summary_keep")
    )

    return {
        "playability_score": playability_score,
        "difficulty_score": difficulty_score,
        "time_estimate_seconds": time_estimate,
        "lang": lang,
        "level_name": level_name,
        "analysis": {
            "path_exists": bool(path),
            "path_length": max(path_length, 0),
            "dead_ends": len([d for d in dead if d not in (start, end)]),
            "empty_rooms": len(_empty_zones(tiles, reachable, occupied, path_set)),
            "enemy_density": enemy_density,
            "treasure_density": treasure_density,
            "trap_density": trap_density,
            "walkable_tiles": walkable,
            "reachable_tiles": len(reachable),
            "enemy_count": len(enemies),
            "treasure_count": len(treasures),
            "trap_count": len(traps),
            "treasure_value": treasure_value,
            "start": list(start) if start else None,
            "end": list(end) if end else None,
        },
        "issues": issues,
        "recommendations": uniq_recs,
        "heatmap": {
            "type": "grid",
            "width": width,
            "height": height,
            "data": heatmap,
            "legend": {
                "0": _t(lang, "heatmap_low"),
                "0.5": _t(lang, "heatmap_mid"),
                "1.0": _t(lang, "heatmap_high"),
            },
        },
        "path": [{"x": x, "y": y} for x, y in (path or [])],
        "summary": summary,
        "methodology": _t(lang, "methodology"),
    }


def compare_levels(
    level_a: dict[str, Any], level_b: dict[str, Any], lang: str | None = None
) -> dict[str, Any]:
    lang = _norm_lang(lang)
    a = analyze_level(level_a, lang=lang)
    b = analyze_level(level_b, lang=lang)
    return {
        "lang": lang,
        "a": {
            "level_name": a.get("level_name"),
            "playability_score": a["playability_score"],
            "difficulty_score": a["difficulty_score"],
            "time_estimate_seconds": a["time_estimate_seconds"],
            "analysis": a["analysis"],
            "issue_count": len(a["issues"]),
        },
        "b": {
            "level_name": b.get("level_name"),
            "playability_score": b["playability_score"],
            "difficulty_score": b["difficulty_score"],
            "time_estimate_seconds": b["time_estimate_seconds"],
            "analysis": b["analysis"],
            "issue_count": len(b["issues"]),
        },
        "delta": {
            "playability": a["playability_score"] - b["playability_score"],
            "difficulty": a["difficulty_score"] - b["difficulty_score"],
            "time_estimate": a["time_estimate_seconds"] - b["time_estimate_seconds"],
            "path_length": a["analysis"]["path_length"] - b["analysis"]["path_length"],
            "enemy_density": round(
                a["analysis"]["enemy_density"] - b["analysis"]["enemy_density"], 3
            ),
        },
    }


async def run_level_analysis(level_data: dict[str, Any], lang: str | None = None) -> dict[str, Any]:
    lang = _norm_lang(lang or level_data.get("lang"))
    base = analyze_level(level_data, lang=lang)
    if settings.USE_MOCK_AI or not settings.OPENAI_API_KEY:
        return base
    try:
        return await _openai_enrich(level_data, base, lang=lang)
    except Exception:
        return base


async def _openai_enrich(level_data: dict[str, Any], base: dict[str, Any], lang: str = "en") -> dict[str, Any]:
    from app.services.openai_client import chat_completion

    lang_name = "Russian" if lang == "ru" else "English"
    prompt = f"""You are a senior level designer. Write ALL narrative in {lang_name}.
Refine the summary and add up to 3 recommendations. Do not contradict the metrics.

Level (truncated):
{json.dumps({k: level_data.get(k) for k in ('level_name','width','height','entities','time_limit')}, ensure_ascii=False)[:4000]}

Analysis:
{json.dumps({k: base[k] for k in ('playability_score','difficulty_score','time_estimate_seconds','issues','recommendations','summary','analysis')}, ensure_ascii=False)[:5000]}

JSON: {{"summary":"...","extra_recommendations":[{{"target","action","location","description"}}]}}"""

    resp = await chat_completion(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content)
    out = dict(base)
    if isinstance(data.get("summary"), str) and data["summary"].strip():
        out["summary"] = data["summary"].strip()
    extras = data.get("extra_recommendations") or []
    if isinstance(extras, list):
        for r in extras[:3]:
            if isinstance(r, dict) and r.get("description"):
                out["recommendations"].append(r)
    out["methodology"] = _t(lang, "methodology_llm")
    return out
