"""AI Game Balancer — metric-driven balance analysis with optional LLM polish."""

from __future__ import annotations

import json
import math
import statistics
from typing import Any

from app.config import get_settings

settings = get_settings()

SEVERITY_WEIGHT = {"high": 12, "medium": 7, "low": 3}


def _f(obj: dict[str, Any], *keys: str, default: float = 0.0) -> float:
    for k in keys:
        if k in obj and obj[k] is not None:
            try:
                return float(obj[k])
            except (TypeError, ValueError):
                continue
    return default


def _name(obj: dict[str, Any], fallback: str = "Item") -> str:
    return str(obj.get("name") or obj.get("id") or fallback)


def _dps(damage: float, speed: float) -> float:
    spd = speed if speed > 0 else 1.0
    return round(damage * spd, 2)


def _survivability(health: float, defense: float, threat_dps: float) -> float:
    """Effective lifetime vs a reference threat DPS."""
    incoming = max(threat_dps - defense * 0.5, threat_dps * 0.25, 0.1)
    return round(health / incoming, 2)


def _ttk(health: float, defense: float, attacker_dps: float) -> float:
    effective_hp = health + defense * 2
    dps = max(attacker_dps, 0.1)
    return round(effective_hp / dps, 2)


def _pct_diff(a: float, b: float) -> float:
    base = max(abs(b), 0.01)
    return round(abs(a - b) / base * 100, 1)


def _mean(vals: list[float]) -> float:
    return statistics.mean(vals) if vals else 0.0


def _stdev(vals: list[float]) -> float:
    return statistics.pstdev(vals) if len(vals) > 1 else 0.0


def analyze_game_data(game_data: dict[str, Any]) -> dict[str, Any]:
    """Deterministic balance analysis. Always available (mock + production base)."""
    classes = list(game_data.get("classes") or [])
    enemies = list(game_data.get("enemies") or [])
    weapons = list(game_data.get("weapons") or [])
    abilities = list(game_data.get("abilities") or [])
    economy = dict(game_data.get("economy") or {})

    issues: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []
    visualizations: list[dict[str, Any]] = []

    # Reference threat from average enemy DPS (or default)
    enemy_dps_list = [_dps(_f(e, "damage"), _f(e, "speed", default=1.0)) for e in enemies]
    threat_dps = _mean(enemy_dps_list) if enemy_dps_list else 12.0

    # ── Classes ──────────────────────────────────────────────────────
    class_metrics: list[dict[str, Any]] = []
    for c in classes:
        dmg = _f(c, "damage")
        spd = _f(c, "speed", default=1.0)
        hp = _f(c, "health", "hp", default=100.0)
        defense = _f(c, "defense", "armour", "armor")
        dps = _dps(dmg, spd)
        surv = _survivability(hp, defense, threat_dps)
        power = round(dps * 0.55 + surv * 0.45, 2)
        class_metrics.append(
            {
                "name": _name(c, "Class"),
                "dps": dps,
                "survivability": surv,
                "power": power,
                "health": hp,
                "damage": dmg,
                "defense": defense,
                "speed": spd,
            }
        )

    if len(class_metrics) >= 2:
        powers = [m["power"] for m in class_metrics]
        avg_p = _mean(powers)
        max_m = max(class_metrics, key=lambda m: m["power"])
        min_m = min(class_metrics, key=lambda m: m["power"])
        spread = _pct_diff(max_m["power"], min_m["power"])
        if spread >= 25:
            sev = "high" if spread >= 40 else "medium"
            issues.append(
                {
                    "type": "class_imbalance",
                    "severity": sev,
                    "description": (
                        f"{max_m['name']} class is {spread}% stronger than {min_m['name']} "
                        f"(power score {max_m['power']} vs {min_m['power']})"
                    ),
                    "details": {
                        "strongest": max_m["name"],
                        "weakest": min_m["name"],
                        "spread_pct": spread,
                        "metrics": {m["name"]: m for m in class_metrics},
                    },
                }
            )
            new_dmg = max(1, round(max_m["damage"] * 0.85, 1))
            recommendations.append(
                {
                    "target": max_m["name"],
                    "action": "reduce_damage",
                    "value": round((1 - new_dmg / max(max_m["damage"], 0.01)) * 100, 1),
                    "description": f"Reduce {max_m['name']} damage from {max_m['damage']} → {new_dmg}",
                }
            )
            new_hp = round(min_m["health"] * 1.15, 1)
            recommendations.append(
                {
                    "target": min_m["name"],
                    "action": "increase_health",
                    "value": 15,
                    "description": f"Increase {min_m['name']} health from {min_m['health']} → {new_hp}",
                }
            )
        cv = (_stdev(powers) / avg_p * 100) if avg_p else 0
        if cv > 20 and spread < 25:
            issues.append(
                {
                    "type": "class_variance",
                    "severity": "low",
                    "description": f"Class power coefficient of variation is {cv:.1f}% (target < 20%)",
                    "details": {"cv_pct": round(cv, 1), "avg_power": round(avg_p, 2)},
                }
            )

        visualizations.append(
            {
                "type": "bar_chart",
                "title": "Class DPS Comparison",
                "data": {
                    "labels": [m["name"] for m in class_metrics],
                    "values": [m["dps"] for m in class_metrics],
                },
            }
        )
        visualizations.append(
            {
                "type": "radar_chart",
                "title": "Class Balance Radar",
                "data": {
                    "labels": ["Damage", "Survivability", "Speed", "Defense", "DPS"],
                    **{
                        m["name"].lower().replace(" ", "_"): [
                            _scale(m["damage"], powers_ref=[x["damage"] for x in class_metrics]),
                            _scale(m["survivability"], powers_ref=[x["survivability"] for x in class_metrics]),
                            _scale(m["speed"], powers_ref=[x["speed"] for x in class_metrics]),
                            _scale(m["defense"], powers_ref=[x["defense"] for x in class_metrics]),
                            _scale(m["dps"], powers_ref=[x["dps"] for x in class_metrics]),
                        ]
                        for m in class_metrics
                    },
                },
            }
        )

    # ── Enemies ──────────────────────────────────────────────────────
    player_dps = _mean([m["dps"] for m in class_metrics]) if class_metrics else 18.0
    player_hp = _mean([m["health"] for m in class_metrics]) if class_metrics else 100.0

    enemy_metrics: list[dict[str, Any]] = []
    for e in enemies:
        hp = _f(e, "health", "hp", default=50.0)
        dmg = _f(e, "damage", default=10.0)
        defense = _f(e, "defense")
        spd = _f(e, "speed", default=1.0)
        xp = _f(e, "xp_reward", "xp", default=0.0)
        gold = _f(e, "gold_reward", "gold", default=0.0)
        edps = _dps(dmg, spd)
        ttk = _ttk(hp, defense, player_dps)
        gold_per_min = round(gold / max(ttk / 60.0, 0.01), 2) if gold else 0.0
        enemy_metrics.append(
            {
                "name": _name(e, "Enemy"),
                "dps": edps,
                "ttk": ttk,
                "gold_per_min": gold_per_min,
                "health": hp,
                "damage": dmg,
                "xp_reward": xp,
                "gold_reward": gold,
            }
        )

        # Too weak: TTK under 3s
        if ttk < 3:
            issues.append(
                {
                    "type": "enemy_too_weak",
                    "severity": "medium",
                    "description": f"{_name(e)} dies too fast (TTK {ttk}s vs player DPS {player_dps})",
                    "details": {
                        "enemy_dps": edps,
                        "player_dps": player_dps,
                        "player_health": player_hp,
                        "time_to_kill": ttk,
                    },
                }
            )
            new_hp = round(hp * 1.2, 1)
            recommendations.append(
                {
                    "target": _name(e),
                    "action": "increase_health",
                    "value": 20,
                    "description": f"Increase {_name(e)} health from {hp} → {new_hp}",
                }
            )
        # Too strong: TTK over 45s or enemy DPS shreds player in < 4s
        player_ttk_by_enemy = _ttk(player_hp, 0, edps)
        if ttk > 45 or player_ttk_by_enemy < 4:
            issues.append(
                {
                    "type": "enemy_too_strong",
                    "severity": "high" if player_ttk_by_enemy < 3 else "medium",
                    "description": (
                        f"{_name(e)} is overtuned (player TTK {ttk}s, "
                        f"player lifetime vs it {player_ttk_by_enemy}s)"
                    ),
                    "details": {
                        "time_to_kill": ttk,
                        "player_lifetime": player_ttk_by_enemy,
                        "enemy_dps": edps,
                    },
                }
            )
            new_dmg = max(1, round(dmg * 0.85, 1))
            recommendations.append(
                {
                    "target": _name(e),
                    "action": "reduce_damage",
                    "value": 15,
                    "description": f"Reduce {_name(e)} damage from {dmg} → {new_dmg}",
                }
            )

    if enemy_metrics:
        visualizations.append(
            {
                "type": "bar_chart",
                "title": "Enemy Time-to-Kill (seconds)",
                "data": {
                    "labels": [m["name"] for m in enemy_metrics],
                    "values": [m["ttk"] for m in enemy_metrics],
                },
            }
        )

    # ── Weapons ──────────────────────────────────────────────────────
    weapon_metrics: list[dict[str, Any]] = []
    for w in weapons:
        dmg = _f(w, "damage", default=10.0)
        spd = _f(w, "speed", "attack_speed", default=1.0)
        price = _f(w, "price", "cost", default=0.0)
        dps = _dps(dmg, spd)
        efficiency = round(dps / max(price, 1.0) * 100, 2) if price else dps
        weapon_metrics.append(
            {
                "name": _name(w, "Weapon"),
                "dps": dps,
                "efficiency": efficiency,
                "damage": dmg,
                "speed": spd,
                "price": price,
                "rarity": w.get("rarity", "common"),
            }
        )

    if len(weapon_metrics) >= 2:
        best = max(weapon_metrics, key=lambda m: m["dps"])
        worst = min(weapon_metrics, key=lambda m: m["dps"])
        spread = _pct_diff(best["dps"], worst["dps"])
        if spread >= 20:
            sev = "high" if spread >= 50 else ("medium" if spread >= 30 else "low")
            issues.append(
                {
                    "type": "weapon_imbalance",
                    "severity": sev,
                    "description": f"{best['name']} has {spread}% more DPS than {worst['name']}",
                    "details": {
                        f"{best['name'].lower()}_dps": best["dps"],
                        f"{worst['name'].lower()}_dps": worst["dps"],
                        "difference": spread,
                    },
                }
            )
            new_dmg = max(1, round(best["damage"] * 0.8, 1))
            recommendations.append(
                {
                    "target": best["name"],
                    "action": "reduce_damage",
                    "value": 20,
                    "description": f"Reduce {best['name']} damage from {best['damage']} → {new_dmg}",
                }
            )

        # Efficiency outliers (DPS per gold)
        if any(m["price"] > 0 for m in weapon_metrics):
            effs = [m["efficiency"] for m in weapon_metrics if m["price"] > 0]
            avg_e = _mean(effs)
            for m in weapon_metrics:
                if m["price"] <= 0:
                    continue
                if m["efficiency"] > avg_e * 1.5:
                    issues.append(
                        {
                            "type": "weapon_efficiency",
                            "severity": "medium",
                            "description": (
                                f"{m['name']} is {round(m['efficiency'] / avg_e * 100 - 100, 1)}% "
                                f"more gold-efficient than average"
                            ),
                            "details": {"efficiency": m["efficiency"], "avg_efficiency": round(avg_e, 2)},
                        }
                    )
                    recommendations.append(
                        {
                            "target": m["name"],
                            "action": "increase_price",
                            "value": 25,
                            "description": f"Raise {m['name']} price from {m['price']} → {round(m['price'] * 1.25)}",
                        }
                    )

        visualizations.append(
            {
                "type": "bar_chart",
                "title": "Weapon DPS Comparison",
                "data": {
                    "labels": [m["name"] for m in weapon_metrics],
                    "values": [m["dps"] for m in weapon_metrics],
                },
            }
        )

    # ── Abilities ────────────────────────────────────────────────────
    ability_metrics: list[dict[str, Any]] = []
    for a in abilities:
        dmg = _f(a, "damage", default=0.0)
        cd = max(_f(a, "cooldown", "cd", default=1.0), 0.5)
        mana = _f(a, "mana_cost", "mana", "cost", default=0.0)
        burst = round(dmg / cd, 2)
        ability_metrics.append(
            {
                "name": _name(a, "Ability"),
                "dps": burst,
                "damage": dmg,
                "cooldown": cd,
                "mana_cost": mana,
            }
        )

    if len(ability_metrics) >= 2:
        best = max(ability_metrics, key=lambda m: m["dps"])
        worst = min(ability_metrics, key=lambda m: m["dps"])
        spread = _pct_diff(best["dps"], worst["dps"])
        if spread >= 40:
            issues.append(
                {
                    "type": "ability_imbalance",
                    "severity": "medium" if spread < 80 else "high",
                    "description": f"{best['name']} sustained DPS is {spread}% above {worst['name']}",
                    "details": {
                        "best_dps": best["dps"],
                        "worst_dps": worst["dps"],
                        "difference": spread,
                    },
                }
            )
            new_cd = round(best["cooldown"] * 1.2, 1)
            recommendations.append(
                {
                    "target": best["name"],
                    "action": "increase_cooldown",
                    "value": 20,
                    "description": f"Increase {best['name']} cooldown from {best['cooldown']} → {new_cd}",
                }
            )

    # ── Economy ──────────────────────────────────────────────────────
    if economy or any(m.get("gold_reward") for m in enemy_metrics):
        starting = _f(economy, "starting_gold", default=100.0)
        gold_kill = _f(economy, "gold_per_kill", default=_mean([m["gold_reward"] for m in enemy_metrics]) if enemy_metrics else 10.0)
        gold_quest = _f(economy, "gold_per_quest", default=50.0)
        xp_level = _f(economy, "xp_per_level", default=100.0)
        price_mult = _f(economy, "price_multiplier", default=1.0)

        avg_weapon_price = _mean([m["price"] for m in weapon_metrics if m["price"] > 0]) or 100.0
        kills_to_weapon = math.ceil((avg_weapon_price * price_mult) / max(gold_kill, 0.01))
        avg_ttk = _mean([m["ttk"] for m in enemy_metrics]) if enemy_metrics else 8.0
        minutes_to_weapon = round(kills_to_weapon * avg_ttk / 60.0, 2)

        if kills_to_weapon <= 2:
            issues.append(
                {
                    "type": "economy_inflation",
                    "severity": "medium",
                    "description": (
                        f"Average weapon affordable after only {kills_to_weapon} kills "
                        f"(~{minutes_to_weapon} min) — economy may inflate too fast"
                    ),
                    "details": {
                        "kills_to_weapon": kills_to_weapon,
                        "minutes_to_weapon": minutes_to_weapon,
                        "gold_per_kill": gold_kill,
                        "avg_weapon_price": avg_weapon_price,
                    },
                }
            )
            recommendations.append(
                {
                    "target": "economy",
                    "action": "reduce_gold_per_kill",
                    "value": 20,
                    "description": f"Reduce gold_per_kill from {gold_kill} → {round(gold_kill * 0.8, 1)}",
                }
            )
        elif kills_to_weapon >= 40:
            issues.append(
                {
                    "type": "economy_too_tight",
                    "severity": "low",
                    "description": f"Needs ~{kills_to_weapon} kills to afford average weapon — progression may feel slow",
                    "details": {"kills_to_weapon": kills_to_weapon, "starting_gold": starting},
                }
            )
            recommendations.append(
                {
                    "target": "economy",
                    "action": "increase_starting_gold",
                    "value": 50,
                    "description": f"Increase starting_gold from {starting} → {starting + 50}",
                }
            )

        if enemy_metrics and xp_level > 0:
            avg_xp = _mean([m["xp_reward"] for m in enemy_metrics]) or 1
            kills_per_level = math.ceil(xp_level / avg_xp)
            if kills_per_level < 3:
                issues.append(
                    {
                        "type": "xp_too_fast",
                        "severity": "medium",
                        "description": f"Level-up in ~{kills_per_level} kills (xp_per_level={xp_level}, avg XP={avg_xp})",
                        "details": {"kills_per_level": kills_per_level, "xp_per_level": xp_level},
                    }
                )

        visualizations.append(
            {
                "type": "bar_chart",
                "title": "Gold per Minute by Enemy",
                "data": {
                    "labels": [m["name"] for m in enemy_metrics],
                    "values": [m["gold_per_min"] for m in enemy_metrics],
                },
            }
        )

    # Deduplicate recommendations by target+action
    seen_rec: set[str] = set()
    uniq_recs: list[dict[str, Any]] = []
    for r in recommendations:
        key = f"{r.get('target')}:{r.get('action')}"
        if key in seen_rec:
            continue
        seen_rec.add(key)
        uniq_recs.append(r)

    # Score
    penalty = sum(SEVERITY_WEIGHT.get(i.get("severity", "low"), 3) for i in issues)
    balance_score = int(max(0, min(100, 100 - penalty)))

    game_name = str(game_data.get("game_name") or "Untitled Game")
    top = [i["description"] for i in issues[:3]]
    summary = (
        f"Overall balance score: {balance_score}/100 for «{game_name}». "
        + (f"Main issues: {'; '.join(top)}. " if top else "No major issues detected. ")
        + (f"Top fix: {uniq_recs[0]['description']}." if uniq_recs else "Keep iterating with playtests.")
    )

    return {
        "balance_score": balance_score,
        "issues": issues,
        "recommendations": uniq_recs,
        "visualizations": visualizations,
        "summary": summary,
        "metrics": {
            "classes": class_metrics,
            "enemies": enemy_metrics,
            "weapons": weapon_metrics,
            "abilities": ability_metrics,
            "threat_dps": threat_dps,
            "player_dps": player_dps,
        },
        "methodology": "Deterministic combat/economy metrics (DPS, TTK, survivability, gold/min)",
    }


def _scale(value: float, powers_ref: list[float], lo: int = 1, hi: int = 10) -> int:
    if not powers_ref:
        return 5
    mn, mx = min(powers_ref), max(powers_ref)
    if mx <= mn:
        return (lo + hi) // 2
    t = (value - mn) / (mx - mn)
    return int(round(lo + t * (hi - lo)))


async def run_balance_analysis(game_data: dict[str, Any]) -> dict[str, Any]:
    """Run balance analysis; optionally enrich narrative via OpenAI when not mocking."""
    base = analyze_game_data(game_data)
    if settings.USE_MOCK_AI:
        return base
    if not settings.OPENAI_API_KEY:
        return base
    try:
        return await _openai_enrich(game_data, base)
    except Exception:
        return base


async def _openai_enrich(game_data: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    from app.services.openai_client import chat_completion

    prompt = f"""You are a senior game designer specializing in combat/economy balance.
Given this game data and a metric-based analysis, refine the summary and add up to 3 extra
actionable recommendations (same JSON shape). Do NOT invent stats that contradict the metrics.
Keep balance_score, issues, visualizations, metrics from the analysis unless clearly wrong.

Game data:
{json.dumps(game_data, ensure_ascii=False)[:6000]}

Analysis:
{json.dumps({k: base[k] for k in ('balance_score', 'issues', 'recommendations', 'summary')}, ensure_ascii=False)[:6000]}

Respond with JSON: {{"summary": "...", "extra_recommendations": [{{"target","action","value","description"}}]}}"""

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
        existing = {(r.get("target"), r.get("action")) for r in out["recommendations"]}
        for r in extras[:3]:
            if not isinstance(r, dict):
                continue
            key = (r.get("target"), r.get("action"))
            if key in existing:
                continue
            out["recommendations"].append(r)
            existing.add(key)
    out["methodology"] = "Deterministic metrics + GPT narrative polish"
    return out
