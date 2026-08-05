"""AI Playtest Analyzer — session metrics, feedback patterns, retention insights."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from app.config import get_settings

settings = get_settings()

_MSG = {
    "en": {
        "methodology": "Deterministic session metrics + feedback keyword mining (+ optional LLM polish)",
        "summary_ok": "{game}: {n} sessions analyzed. Completion {comp}% · avg deaths {deaths} · rating {rating}/5.",
        "summary_issues": "{game}: {n} sessions. {high} high-severity issues found — start with drop-off and death spikes.",
        "insight_boss_deaths": "Players die {ratio}× more often at {loc} than at other boss/combat hotspots",
        "insight_tutorial": "Tutorial/onboarding confusion appears in {pct}% of feedback comments",
        "insight_combat_pos": "Combat is among the most praised themes ({pct}% of tagged feedback)",
        "insight_quit_early": "{pct}% of sessions end with quit before completion",
        "insight_long_sessions": "Average session length is {mins} min — check pacing if this feels too long",
        "insight_unused": "Event type “{ev}” is rare ({count} times) — mechanic may be underused",
        "issue_high_diff": "{loc}: {pct}% of sessions that reach it die at least once",
        "issue_dropoff": "Sharp drop-off near {loc} ({pct}% leave around this phase)",
        "issue_low_rating": "Average rating {rating}/5 — sentiment is below a healthy playtest bar",
        "issue_confusing": "“{tag}” mentioned in {pct}% of feedback — clarity / UX friction",
        "issue_completion": "Completion rate is only {pct}% — design or difficulty may be blocking players",
        "rec_reduce_diff": "Reduce difficulty at {target}: lower HP/damage ~15–25% and telegraph attacks more clearly",
        "rec_tutorial": "Clarify tutorial: add visual cues, shorter steps, and a skippable advanced tip layer",
        "rec_ui": "Improve {target}: tooltips, stronger affordances, and confirm destructive actions",
        "rec_retention": "Add a mid-session reward or difficulty soft-cap before the {target} drop-off",
        "rec_praise": "Lean into {target}: feature it in onboarding and store copy — players already like it",
        "rec_unused": "Surface or buff “{target}” so players discover it earlier",
        "viz_deaths": "Death / quit density by event type",
        "viz_retention": "Session funnel (start → milestones → complete/quit)",
        "viz_ratings": "Feedback rating distribution",
        "loc_unknown": "Unknown hotspot",
        "loc_boss": "Boss encounter",
        "loc_combat": "Combat",
        "loc_tutorial": "Tutorial",
        "loc_early": "Early session",
        "sev_high": "high",
        "sev_medium": "medium",
        "sev_low": "low",
    },
    "ru": {
        "methodology": "Детерминированные метрики сессий + разбор отзывов (+ опциональная LLM-доработка)",
        "summary_ok": "{game}: проанализировано сессий: {n}. Прохождение {comp}% · ср. смертей {deaths} · оценка {rating}/5.",
        "summary_issues": "{game}: сессий {n}. Критичных проблем: {high} — начните с оттока и пиков смертей.",
        "insight_boss_deaths": "Игроки умирают в {ratio}× чаще в зоне «{loc}», чем в других боевых точках",
        "insight_tutorial": "Путаница с туториалом/онбордингом в {pct}% отзывов",
        "insight_combat_pos": "Боёвка среди самых хвалимых тем ({pct}% отзывов с тегами)",
        "insight_quit_early": "{pct}% сессий заканчиваются выходом до прохождения",
        "insight_long_sessions": "Средняя длина сессии {mins} мин — проверьте темп, если это слишком долго",
        "insight_unused": "Событие «{ev}» редко ({count} раз) — механика может быть незаметной",
        "issue_high_diff": "{loc}: в {pct}% сессий, дошедших сюда, есть хотя бы одна смерть",
        "issue_dropoff": "Резкий отток около «{loc}» ({pct}% уходят на этом этапе)",
        "issue_low_rating": "Средняя оценка {rating}/5 — тональность ниже здорового плейтеста",
        "issue_confusing": "Тег «{tag}» в {pct}% отзывов — проблемы ясности / UX",
        "issue_completion": "Прохождение всего {pct}% — дизайн или сложность блокируют игроков",
        "rec_reduce_diff": "Снизьте сложность в «{target}»: HP/урон −15–25% и более читаемые атаки",
        "rec_tutorial": "Упростите туториал: визуальные подсказки, короткие шаги, опциональные советы",
        "rec_ui": "Улучшите «{target}»: тултипы, понятные аффордансы, подтверждение опасных действий",
        "rec_retention": "Добавьте награду или смягчение сложности до точки оттока «{target}»",
        "rec_praise": "Усильте «{target}» в онбординге и сторе — игроки уже хвалят",
        "rec_unused": "Подсветите или усильте «{target}», чтобы игроки находили раньше",
        "viz_deaths": "Плотность смертей / выходов по типу события",
        "viz_retention": "Воронка сессии (старт → этапы → complete/quit)",
        "viz_ratings": "Распределение оценок",
        "loc_unknown": "Неизвестная точка",
        "loc_boss": "Босс",
        "loc_combat": "Бой",
        "loc_tutorial": "Туториал",
        "loc_early": "Начало сессии",
        "sev_high": "высокий",
        "sev_medium": "средний",
        "sev_low": "низкий",
    },
}

_NEGATIVE = {
    "en": (
        "hard",
        "impossible",
        "frustrating",
        "confusing",
        "bug",
        "broken",
        "unfair",
        "quit",
        "gave up",
        "boring",
        "unclear",
        "slow",
        "lag",
    ),
    "ru": (
        "сложно",
        "невозможно",
        "бесит",
        "путаница",
        "баг",
        "сломано",
        "нечестно",
        "бросил",
        "скучно",
        "непонятно",
        "медленно",
        "лагает",
        "раздражает",
    ),
}

_POSITIVE = {
    "en": ("great", "fun", "smooth", "love", "awesome", "satisfying", "polished", "cool"),
    "ru": ("отлично", "круто", "гладко", "люблю", "кайф", "приятно", "полировано", "классно"),
}


def _norm_lang(lang: str | None) -> str:
    return "ru" if str(lang or "").lower().startswith("ru") else "en"


def _t(lang: str, key: str, **kwargs: Any) -> str:
    table = _MSG.get(_norm_lang(lang), _MSG["en"])
    tpl = table.get(key) or _MSG["en"].get(key) or key
    try:
        return tpl.format(**kwargs)
    except Exception:
        return tpl


def _sessions(data: dict[str, Any]) -> list[dict[str, Any]]:
    raw = data.get("sessions") or []
    if not isinstance(raw, list):
        return []
    return [s for s in raw if isinstance(s, dict)]


def _feedback(session: dict[str, Any]) -> dict[str, Any]:
    fb = session.get("feedback") or {}
    return fb if isinstance(fb, dict) else {}


def _events(session: dict[str, Any]) -> list[dict[str, Any]]:
    ev = session.get("events") or []
    if not isinstance(ev, list):
        return []
    return [e for e in ev if isinstance(e, dict)]


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        if v is None:
            return default
        return int(v)
    except (TypeError, ValueError):
        return default


def _pct(n: float, d: float) -> float:
    if d <= 0:
        return 0.0
    return round(100.0 * n / d, 1)


def _location_from_event(ev: dict[str, Any], lang: str) -> str:
    for key in ("location", "name", "label", "id"):
        val = ev.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    et = str(ev.get("type") or "").lower()
    if et == "boss":
        return _t(lang, "loc_boss")
    if et == "combat":
        return _t(lang, "loc_combat")
    if et in ("tutorial", "onboarding"):
        return _t(lang, "loc_tutorial")
    if et:
        return et.replace("_", " ").title()
    return _t(lang, "loc_unknown")


def _summary_stats(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(sessions)
    if n == 0:
        return {
            "total_sessions": 0,
            "average_duration": 0,
            "average_deaths": 0,
            "completion_rate": 0,
            "average_rating": 0,
            "drop_off_rate": 0,
            "total_playtime_seconds": 0,
        }

    durations = [_safe_int(s.get("duration_seconds")) for s in sessions]
    deaths = [_safe_int(s.get("deaths")) for s in sessions]
    completed = 0
    ratings: list[float] = []
    for s in sessions:
        ct = s.get("completion_time")
        ev_types = {str(e.get("type") or "").lower() for e in _events(s)}
        if ct is not None or "complete" in ev_types:
            completed += 1
        rating = _feedback(s).get("rating")
        if rating is not None:
            ratings.append(_safe_float(rating))

    avg_dur = round(sum(durations) / n)
    avg_deaths = round(sum(deaths) / n, 2)
    comp = _pct(completed, n)
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0
    return {
        "total_sessions": n,
        "average_duration": avg_dur,
        "average_deaths": avg_deaths,
        "completion_rate": comp,
        "average_rating": avg_rating,
        "drop_off_rate": round(100.0 - comp, 1),
        "total_playtime_seconds": sum(durations),
        "rated_sessions": len(ratings),
    }


def _death_hotspots(sessions: list[dict[str, Any]], lang: str) -> Counter:
    counts: Counter = Counter()
    for s in sessions:
        events = _events(s)
        last_loc = _t(lang, "loc_early")
        for ev in events:
            et = str(ev.get("type") or "").lower()
            if et in ("boss", "combat", "trap", "enemy", "hazard", "level", "checkpoint"):
                last_loc = _location_from_event(ev, lang)
            if et == "death":
                counts[last_loc] += 1
            if et == "quit":
                counts[f"quit@{last_loc}"] += 1
    return counts


def _event_type_counts(sessions: list[dict[str, Any]]) -> Counter:
    c: Counter = Counter()
    for s in sessions:
        for ev in _events(s):
            et = str(ev.get("type") or "unknown").lower()
            c[et] += 1
    return c


def _feedback_tag_counts(sessions: list[dict[str, Any]]) -> Counter:
    c: Counter = Counter()
    for s in sessions:
        tags = _feedback(s).get("tags") or []
        if isinstance(tags, list):
            for tag in tags:
                t = str(tag).strip().lower()
                if t:
                    c[t] += 1
    return c


def _comment_hits(sessions: list[dict[str, Any]], words: tuple[str, ...]) -> int:
    hits = 0
    for s in sessions:
        comment = str(_feedback(s).get("comment") or "").lower()
        if any(w in comment for w in words):
            hits += 1
    return hits


def _retention_funnel(sessions: list[dict[str, Any]], lang: str) -> dict[str, Any]:
    """Approximate funnel from event types across sessions."""
    milestones = ["start", "combat", "treasure", "boss", "complete", "quit"]
    labels_en = ["Start", "Combat", "Loot", "Boss", "Complete", "Quit"]
    labels_ru = ["Старт", "Бой", "Лут", "Босс", "Финиш", "Выход"]
    labels = labels_ru if lang == "ru" else labels_en
    n = max(len(sessions), 1)
    values = []
    for m in milestones:
        reached = 0
        for s in sessions:
            types = {str(e.get("type") or "").lower() for e in _events(s)}
            if m == "start":
                reached += 1 if ("start" in types or True) else 0
            else:
                reached += 1 if m in types else 0
        values.append(round(100.0 * reached / n, 1) if m != "start" else 100.0)
    # Start always 100
    values[0] = 100.0
    return {"labels": labels, "values": values, "milestones": milestones}


def _rating_dist(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    buckets = {str(i): 0 for i in range(1, 6)}
    for s in sessions:
        r = _feedback(s).get("rating")
        if r is None:
            continue
        key = str(max(1, min(5, int(round(_safe_float(r))))))
        buckets[key] += 1
    return {"labels": list(buckets.keys()), "values": list(buckets.values())}


def _build_insights_issues_recs(
    sessions: list[dict[str, Any]],
    summary: dict[str, Any],
    lang: str,
) -> tuple[list[dict], list[dict], list[dict]]:
    insights: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    recs: list[dict[str, Any]] = []
    n = summary["total_sessions"]
    if n == 0:
        return insights, issues, recs

    deaths = _death_hotspots(sessions, lang)
    pure_deaths = Counter({k: v for k, v in deaths.items() if not str(k).startswith("quit@")})
    event_counts = _event_type_counts(sessions)
    tags = _feedback_tag_counts(sessions)
    fb_n = sum(1 for s in sessions if _feedback(s).get("comment") or _feedback(s).get("tags"))

    # Boss / hotspot spike
    if pure_deaths:
        top_loc, top_n = pure_deaths.most_common(1)[0]
        others = sum(v for k, v in pure_deaths.items() if k != top_loc)
        avg_others = others / max(len(pure_deaths) - 1, 1)
        ratio = round(top_n / avg_others, 1) if avg_others > 0 else float(top_n)
        if ratio >= 2 or top_n >= max(3, n):
            insights.append(
                {
                    "type": "difficulty_spike",
                    "severity": "high",
                    "description": _t(lang, "insight_boss_deaths", ratio=ratio, loc=top_loc),
                    "location": top_loc,
                    "details": {"deaths_at_hotspot": top_n, "deaths_elsewhere": others, "ratio": ratio},
                }
            )
            # sessions that saw this location via boss/combat naming is approximate
            died_pct = _pct(top_n, max(n, 1))
            # better: share of sessions with ≥1 death overall if hotspot heavy
            sessions_with_death = sum(1 for s in sessions if _safe_int(s.get("deaths")) > 0)
            impact_pct = _pct(sessions_with_death, n)
            issues.append(
                {
                    "type": "high_difficulty",
                    "severity": "high",
                    "description": _t(lang, "issue_high_diff", loc=top_loc, pct=max(died_pct, impact_pct)),
                    "location": top_loc,
                    "impact": f"{summary['drop_off_rate']}% drop-off",
                }
            )
            recs.append(
                {
                    "target": top_loc,
                    "action": "reduce_difficulty",
                    "description": _t(lang, "rec_reduce_diff", target=top_loc),
                }
            )

    # Quit early
    quit_sessions = sum(1 for s in sessions if "quit" in {str(e.get("type") or "").lower() for e in _events(s)})
    quit_pct = _pct(quit_sessions, n)
    if quit_pct >= 20:
        quit_locs = Counter({k.replace("quit@", ""): v for k, v in deaths.items() if str(k).startswith("quit@")})
        loc = quit_locs.most_common(1)[0][0] if quit_locs else _t(lang, "loc_early")
        insights.append(
            {
                "type": "early_quit",
                "severity": "high" if quit_pct >= 40 else "medium",
                "description": _t(lang, "insight_quit_early", pct=quit_pct),
                "location": loc,
                "details": {"quit_sessions": quit_sessions, "quit_rate": quit_pct},
            }
        )
        issues.append(
            {
                "type": "drop_off",
                "severity": "high" if quit_pct >= 40 else "medium",
                "description": _t(lang, "issue_dropoff", loc=loc, pct=quit_pct),
                "location": loc,
                "impact": f"{quit_pct}% quit rate",
            }
        )
        recs.append(
            {
                "target": loc,
                "action": "improve_retention",
                "description": _t(lang, "rec_retention", target=loc),
            }
        )

    # Completion
    if summary["completion_rate"] < 60 and n >= 2:
        issues.append(
            {
                "type": "low_completion",
                "severity": "high" if summary["completion_rate"] < 40 else "medium",
                "description": _t(lang, "issue_completion", pct=summary["completion_rate"]),
                "location": _t(lang, "loc_boss"),
                "impact": f"{summary['drop_off_rate']}% drop-off",
            }
        )

    # Tutorial / confusing tags
    confusing_tags = {"tutorial", "confusing", "ui", "inventory", "onboarding", "unclear", "туториал", "путаница"}
    confuse_hits = sum(tags[t] for t in confusing_tags if t in tags)
    comment_confuse = _comment_hits(
        sessions,
        ("tutorial", "confusing", "unclear", "inventory", "туториал", "путаница", "непонят"),
    )
    mention_n = max(confuse_hits, comment_confuse)
    if fb_n and mention_n:
        pct = _pct(mention_n, fb_n)
        if pct >= 15:
            insights.append(
                {
                    "type": "confusing_tutorial",
                    "severity": "medium",
                    "description": _t(lang, "insight_tutorial", pct=pct),
                    "location": _t(lang, "loc_tutorial"),
                    "details": {"feedback_mentions": mention_n, "total_feedback": fb_n},
                }
            )
            issues.append(
                {
                    "type": "confusing_ui",
                    "severity": "medium",
                    "description": _t(lang, "issue_confusing", tag="tutorial/ui", pct=pct),
                    "location": _t(lang, "loc_tutorial"),
                    "impact": "Reduces onboarding clarity" if lang != "ru" else "Снижает ясность онбординга",
                }
            )
            recs.append(
                {
                    "target": _t(lang, "loc_tutorial"),
                    "action": "improve_clarity",
                    "description": _t(lang, "rec_tutorial"),
                }
            )

    # Positive combat
    pos_tags = {"combat", "fun", "smooth", "controls", "бой", "управление"}
    pos_n = sum(tags[t] for t in pos_tags if t in tags)
    pos_comments = _comment_hits(sessions, _POSITIVE[lang] + ("combat", "бой", "smooth", "гладк"))
    if fb_n and (pos_n or pos_comments):
        pct = _pct(max(pos_n, pos_comments), fb_n)
        if pct >= 20:
            insights.append(
                {
                    "type": "positive_combat",
                    "severity": "low",
                    "description": _t(lang, "insight_combat_pos", pct=pct),
                    "location": _t(lang, "loc_combat"),
                    "details": {"positive_mentions": max(pos_n, pos_comments), "total_feedback": fb_n},
                }
            )
            recs.append(
                {
                    "target": _t(lang, "loc_combat"),
                    "action": "amplify_strength",
                    "description": _t(lang, "rec_praise", target=_t(lang, "loc_combat")),
                }
            )

    # Low rating
    if summary["average_rating"] and summary["average_rating"] < 3.2 and summary.get("rated_sessions", 0) >= 1:
        issues.append(
            {
                "type": "low_rating",
                "severity": "high" if summary["average_rating"] < 2.5 else "medium",
                "description": _t(lang, "issue_low_rating", rating=summary["average_rating"]),
                "location": "Feedback",
                "impact": f"avg {summary['average_rating']}/5",
            }
        )

    # Long sessions
    if summary["average_duration"] >= 2400:
        mins = round(summary["average_duration"] / 60)
        insights.append(
            {
                "type": "long_sessions",
                "severity": "low",
                "description": _t(lang, "insight_long_sessions", mins=mins),
                "location": "Pacing",
                "details": {"average_duration": summary["average_duration"]},
            }
        )

    # Underused events
    common = {"start", "death", "respawn", "quit", "complete", "combat"}
    for ev, count in event_counts.most_common():
        if ev in common:
            continue
        if 0 < count <= max(1, n // 5):
            insights.append(
                {
                    "type": "underused_mechanic",
                    "severity": "low",
                    "description": _t(lang, "insight_unused", ev=ev, count=count),
                    "location": ev,
                    "details": {"event_count": count},
                }
            )
            recs.append(
                {
                    "target": ev,
                    "action": "surface_mechanic",
                    "description": _t(lang, "rec_unused", target=ev),
                }
            )
            break

    # Dedup recommendations by target+action
    seen = set()
    uniq_recs = []
    for r in recs:
        key = (r.get("target"), r.get("action"))
        if key in seen:
            continue
        seen.add(key)
        uniq_recs.append(r)

    return insights[:8], issues[:8], uniq_recs[:8]


def _heatmap_from_deaths(sessions: list[dict[str, Any]], size: int = 10) -> list[list[int]]:
    """Synthetic heatmap: map death timestamps into a grid for UI."""
    grid = [[0 for _ in range(size)] for _ in range(size)]
    for s in sessions:
        for ev in _events(s):
            if str(ev.get("type") or "").lower() != "death":
                continue
            ts = _safe_float(ev.get("timestamp"))
            # Prefer explicit coords if present
            if "x" in ev and "y" in ev:
                x = int(max(0, min(size - 1, _safe_int(ev.get("x")) % size)))
                y = int(max(0, min(size - 1, _safe_int(ev.get("y")) % size)))
            else:
                x = int(ts) % size
                y = int(ts // 7) % size
            grid[y][x] += 1
    return grid


def analyze_playtest(playtest_data: dict[str, Any], lang: str | None = None) -> dict[str, Any]:
    lang = _norm_lang(lang or playtest_data.get("lang"))
    game = str(playtest_data.get("game_name") or "Game")
    sessions = _sessions(playtest_data)
    summary = _summary_stats(sessions)
    insights, issues, recommendations = _build_insights_issues_recs(sessions, summary, lang)

    death_counts = _death_hotspots(sessions, lang)
    pure = [(k, v) for k, v in death_counts.most_common(8) if not str(k).startswith("quit@")]
    if not pure:
        pure = [("—", 0)]
    funnel = _retention_funnel(sessions, lang)
    ratings = _rating_dist(sessions)

    visualizations = [
        {
            "type": "bar_chart",
            "title": _t(lang, "viz_deaths"),
            "data": {"labels": [k for k, _ in pure], "values": [v for _, v in pure]},
        },
        {
            "type": "line_chart",
            "title": _t(lang, "viz_retention"),
            "data": {"labels": funnel["labels"], "values": funnel["values"]},
        },
        {
            "type": "bar_chart",
            "title": _t(lang, "viz_ratings"),
            "data": ratings,
        },
        {
            "type": "heatmap",
            "title": "Death heatmap" if lang != "ru" else "Тепловая карта смертей",
            "data": _heatmap_from_deaths(sessions),
        },
    ]

    high = sum(1 for i in issues if i.get("severity") == "high")
    if high:
        text_summary = _t(lang, "summary_issues", game=game, n=summary["total_sessions"], high=high)
    else:
        text_summary = _t(
            lang,
            "summary_ok",
            game=game,
            n=summary["total_sessions"],
            comp=summary["completion_rate"],
            deaths=summary["average_deaths"],
            rating=summary["average_rating"],
        )

    health = 100
    health -= min(40, high * 12)
    health -= min(25, max(0, 60 - summary["completion_rate"]) * 0.5)
    if summary["average_rating"] and summary["average_rating"] < 3.5:
        health -= min(20, (3.5 - summary["average_rating"]) * 10)
    health = int(max(0, min(100, round(health))))

    return {
        "game_name": game,
        "lang": lang,
        "summary": summary,
        "insights": insights,
        "issues": issues,
        "recommendations": recommendations,
        "visualizations": visualizations,
        "health_score": health,
        "summary_text": text_summary,
        "summary_narrative": text_summary,
        "methodology": _t(lang, "methodology"),
        "event_counts": dict(_event_type_counts(sessions)),
        "feedback_tags": dict(_feedback_tag_counts(sessions)),
    }


async def run_playtest_analysis(playtest_data: dict[str, Any], lang: str | None = None) -> dict[str, Any]:
    lang = _norm_lang(lang or playtest_data.get("lang"))
    base = analyze_playtest(playtest_data, lang=lang)
    if settings.USE_MOCK_AI or not settings.OPENAI_API_KEY:
        return base
    try:
        return await _openai_enrich(playtest_data, base, lang)
    except Exception:
        return base


async def _openai_enrich(playtest_data: dict[str, Any], base: dict[str, Any], lang: str) -> dict[str, Any]:
    from app.services.openai_client import chat_completion

    lang_name = "Russian" if lang == "ru" else "English"
    compact = {
        "game_name": playtest_data.get("game_name"),
        "summary": base.get("summary"),
        "insights": base.get("insights")[:5],
        "issues": base.get("issues")[:5],
        "recommendations": base.get("recommendations")[:5],
        "session_sample": (_sessions(playtest_data) or [])[:3],
    }
    prompt = f"""You are a senior game designer reviewing playtest analytics.
Write ALL narrative fields in {lang_name}.
Improve summary_text and optionally add up to 3 extra_recommendations (objects with target, action, description).
Do not invent metrics that contradict the provided summary numbers.

Data:
{json.dumps(compact, ensure_ascii=False)[:6000]}

Respond JSON only:
{{"summary_text":"...","extra_recommendations":[{{"target":"...","action":"...","description":"..."}}]}}"""

    resp = await chat_completion(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content)
    out = dict(base)
    if isinstance(data.get("summary_text"), str) and data["summary_text"].strip():
        out["summary_text"] = data["summary_text"].strip()
        out["summary_narrative"] = out["summary_text"]
    extra = data.get("extra_recommendations")
    if isinstance(extra, list) and extra:
        recs = list(out.get("recommendations") or [])
        for item in extra[:3]:
            if isinstance(item, dict) and item.get("description"):
                recs.append(
                    {
                        "target": str(item.get("target") or "Design"),
                        "action": str(item.get("action") or "improve"),
                        "description": str(item["description"]),
                    }
                )
        out["recommendations"] = recs[:10]
    out["methodology"] = (
        "LLM-enriched playtest analysis"
        if lang != "ru"
        else "LLM-обогащённый анализ плейтеста"
    )
    return out
