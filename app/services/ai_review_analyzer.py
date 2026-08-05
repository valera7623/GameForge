"""AI Review Analyzer — sentiment, categories, trends, issues & praises from player reviews."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from typing import Any

from app.config import get_settings

settings = get_settings()

SOURCES = ("steam", "appstore", "googleplay", "custom")

_CATEGORIES = {
    "difficulty": {
        "en": ("hard", "difficult", "unfair", "impossible", "boss", "died", "die", "too hard", "brutal"),
        "ru": ("сложно", "сложный", "нечестно", "невозможно", "босс", "умер", "умерла", "слишком сложно"),
        "label_en": "Difficulty",
        "label_ru": "Сложность",
    },
    "combat": {
        "en": ("combat", "fight", "fighting", "controls", "smooth", "melee", "gunplay"),
        "ru": ("бой", "боёвка", "сражение", "управление", "гладко", "комбат"),
        "label_en": "Combat",
        "label_ru": "Боёвка",
    },
    "ui": {
        "en": ("ui", "ux", "inventory", "menu", "interface", "confusing", "clutter"),
        "ru": ("интерфейс", "инвентарь", "меню", "ui", "путаница", "непонятно"),
        "label_en": "UI/UX",
        "label_ru": "UI/UX",
    },
    "story": {
        "en": ("story", "lore", "narrative", "characters", "plot"),
        "ru": ("сюжет", "история", "лор", "персонаж", "нарратив"),
        "label_en": "Story",
        "label_ru": "Сюжет",
    },
    "performance": {
        "en": ("bug", "bugs", "crash", "fps", "lag", "performance", "optimize", "stutter"),
        "ru": ("баг", "баги", "краш", "лаг", "лаги", "производительность", "фпс", "тормоза"),
        "label_en": "Performance",
        "label_ru": "Производительность",
    },
    "content": {
        "en": ("procedural", "replay", "loot", "dungeon", "content", "hours", "generation"),
        "ru": ("процедур", "реиграбельность", "лут", "подземель", "контент", "часов", "генерац"),
        "label_en": "Content",
        "label_ru": "Контент",
    },
    "tutorial": {
        "en": ("tutorial", "onboarding", "beginner", "new player", "learn"),
        "ru": ("туториал", "обучение", "новичок", "онбординг"),
        "label_en": "Tutorial",
        "label_ru": "Туториал",
    },
}

_ISSUE_PATTERNS = [
    {
        "id": "boss_hard",
        "en_kw": ("boss", "unfair", "impossible", "too hard", "died"),
        "ru_kw": ("босс", "нечестн", "невозможн", "слишком слож", "умер"),
        "label_en": "Boss / peak difficulty feels unfair",
        "label_ru": "Босс / пик сложности ощущается нечестным",
        "target_en": "Boss difficulty",
        "target_ru": "Сложность босса",
        "action": "reduce_difficulty",
        "rec_en": "Reduce peak encounter HP/damage ~15–25% and telegraph attacks more clearly",
        "rec_ru": "Снизьте HP/урон пиковых энкаунтеров на 15–25% и сделайте атаки читаемее",
    },
    {
        "id": "inventory_ui",
        "en_kw": ("inventory", "ui", "menu", "confusing", "mess", "clutter"),
        "ru_kw": ("инвентар", "интерфейс", "меню", "путаниц", "непонят"),
        "label_en": "Inventory / UI is confusing",
        "label_ru": "Инвентарь / UI запутанный",
        "target_en": "Inventory UI",
        "target_ru": "Инвентарь / UI",
        "action": "redesign",
        "rec_en": "Add categories, search, and clearer item affordances in inventory",
        "rec_ru": "Добавьте категории, поиск и более понятные аффордансы в инвентаре",
    },
    {
        "id": "tutorial",
        "en_kw": ("tutorial", "confusing", "unclear", "onboarding"),
        "ru_kw": ("туториал", "обучен", "путаниц", "непонят"),
        "label_en": "Tutorial is confusing",
        "label_ru": "Туториал запутанный",
        "target_en": "Tutorial",
        "target_ru": "Туториал",
        "action": "improve_clarity",
        "rec_en": "Shorten tutorial steps and add visual indicators / optional advanced tips",
        "rec_ru": "Сократите шаги туториала и добавьте визуальные подсказки",
    },
    {
        "id": "bugs",
        "en_kw": ("bug", "bugs", "crash", "broken", "glitch"),
        "ru_kw": ("баг", "баги", "краш", "сломано", "глюч"),
        "label_en": "Bugs / instability",
        "label_ru": "Баги / нестабильность",
        "target_en": "Stability",
        "target_ru": "Стабильность",
        "action": "fix_bugs",
        "rec_en": "Triage top crash/bug reports and ship a hotfix for the most mentioned ones",
        "rec_ru": "Соберите топ крашей/багов и выпустите хотфикс по самым частым",
    },
    {
        "id": "early_balance",
        "en_kw": ("early", "too strong", "overpowered", "enemies", "levels"),
        "ru_kw": ("ранн", "слишком сильн", "враг", "уровн"),
        "label_en": "Early-game enemy balance",
        "label_ru": "Баланс врагов на старте",
        "target_en": "Early combat",
        "target_ru": "Ранний бой",
        "action": "rebalance",
        "rec_en": "Softer early enemy curve; delay spike encounters by 1–2 areas",
        "rec_ru": "Смягчите раннюю кривую врагов; отодвиньте пики на 1–2 зоны",
    },
]

_PRAISE_PATTERNS = [
    {
        "id": "procgen",
        "en_kw": ("procedural", "generated", "every run", "replay"),
        "ru_kw": ("процедур", "генерац", "каждый забег", "реиграб"),
        "label_en": "Procedural generation / replayability",
        "label_ru": "Процедурная генерация / реиграбельность",
        "target_en": "Procedural content",
        "target_ru": "Процедурный контент",
        "action": "amplify_strength",
        "rec_en": "Feature procedural variety in store copy, trailers, and onboarding",
        "rec_ru": "Подчеркните процедурное разнообразие в сторе, трейлерах и онбординге",
    },
    {
        "id": "combat_smooth",
        "en_kw": ("combat", "smooth", "controls", "satisfying", "fun"),
        "ru_kw": ("бой", "боёвка", "гладко", "управление", "кайф", "приятн"),
        "label_en": "Combat feels smooth",
        "label_ru": "Боёвка ощущается гладкой",
        "target_en": "Combat",
        "target_ru": "Боёвка",
        "action": "amplify_strength",
        "rec_en": "Lead marketing and vertical slice with combat feel clips",
        "rec_ru": "В маркетинге и вертикальном срезе ведите с кадрами ощущения боя",
    },
    {
        "id": "hours",
        "en_kw": ("hours", "addictive", "recommend", "amazing", "love"),
        "ru_kw": ("часов", "рекоменд", "отличн", "люблю", "кайф"),
        "label_en": "High engagement / recommend",
        "label_ru": "Высокая вовлечённость / рекомендации",
        "target_en": "Retention hooks",
        "target_ru": "Крючки удержания",
        "action": "double_down",
        "rec_en": "Add mid/late-game goals that extend the praised loop safely",
        "rec_ru": "Добавьте цели mid/late game, которые аккуратно удлиняют хвалёный луп",
    },
]

_POS_WORDS = {
    "en": ("amazing", "great", "love", "excellent", "smooth", "fun", "recommend", "perfect", "awesome", "good"),
    "ru": ("отличн", "класс", "люблю", "гладко", "кайф", "рекоменд", "супер", "хорош", "прекрасно", "неплох"),
}
_NEG_WORDS = {
    "en": ("bad", "hate", "awful", "terrible", "unfair", "broken", "confusing", "boring", "crash", "refund", "gave up"),
    "ru": ("плох", "ужас", "бесит", "нечестн", "сломано", "путаниц", "скучн", "краш", "бросил", "баг"),
}

_MSG = {
    "en": {
        "methodology": "Keyword sentiment + category mining over review texts (+ optional LLM polish)",
        "summary_ok": "{game}: {n} reviews · avg {rating}/5 · {pos}% positive sentiment.",
        "summary_issues": "{game}: {n} reviews · {issues} top issues flagged — start with the highest severity.",
        "trend_up": "increasing",
        "trend_down": "decreasing",
        "trend_stable": "stable",
        "viz_sentiment": "Sentiment mix",
        "viz_rating": "Rating trend",
        "viz_categories": "Category volume",
    },
    "ru": {
        "methodology": "Keyword-тональность + категории по текстам отзывов (+ опциональная LLM-доработка)",
        "summary_ok": "{game}: отзывов {n} · ср. {rating}/5 · позитив {pos}%.",
        "summary_issues": "{game}: отзывов {n} · проблем в топе: {issues} — начните с самых критичных.",
        "trend_up": "растёт",
        "trend_down": "падает",
        "trend_stable": "стабильно",
        "viz_sentiment": "Тональность",
        "viz_rating": "Тренд оценок",
        "viz_categories": "Объём по категориям",
    },
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


def _norm_source(source: str | None) -> str:
    s = str(source or "custom").lower().replace(" ", "").replace("_", "")
    aliases = {
        "steam": "steam",
        "appstore": "appstore",
        "ios": "appstore",
        "apple": "appstore",
        "googleplay": "googleplay",
        "google": "googleplay",
        "android": "googleplay",
        "custom": "custom",
    }
    return aliases.get(s, "custom")


def _reviews(data: dict[str, Any]) -> list[dict[str, Any]]:
    raw = data.get("reviews") or []
    if not isinstance(raw, list):
        return []
    out = []
    for i, r in enumerate(raw):
        if not isinstance(r, dict):
            continue
        text = str(r.get("text") or r.get("review") or r.get("content") or "").strip()
        if not text:
            continue
        rating = r.get("rating")
        try:
            rating_i = int(rating) if rating is not None else None
        except (TypeError, ValueError):
            rating_i = None
        if rating_i is not None:
            rating_i = max(1, min(5, rating_i))
        out.append(
            {
                "review_id": str(r.get("review_id") or r.get("id") or f"rev_{i+1}"),
                "rating": rating_i,
                "text": text,
                "date": str(r.get("date") or r.get("created_at") or "")[:32],
                "language": str(r.get("language") or r.get("lang") or "").lower()[:8] or _detect_lang(text),
            }
        )
    return out


def _detect_lang(text: str) -> str:
    return "ru" if re.search(r"[А-Яа-яЁё]", text) else "en"


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _pct(n: float, d: float) -> float:
    if d <= 0:
        return 0.0
    return round(100.0 * n / d, 1)


def _word_hits(text: str, words: tuple[str, ...]) -> int:
    low = text.lower()
    return sum(1 for w in words if w in low)


def _classify_sentiment(review: dict[str, Any]) -> str:
    text = review["text"]
    lang = "ru" if review.get("language", "").startswith("ru") else "en"
    pos = _word_hits(text, _POS_WORDS[lang])
    neg = _word_hits(text, _NEG_WORDS[lang])
    rating = review.get("rating")
    if rating is not None:
        if rating >= 4:
            pos += 2
        elif rating <= 2:
            neg += 2
        else:
            return "neutral" if abs(pos - neg) <= 1 else ("positive" if pos > neg else "negative")
    if pos > neg + 0:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def _sentiment_score_1_5(label: str, rating: int | None) -> float:
    if rating is not None:
        return float(rating)
    return {"positive": 4.5, "neutral": 3.0, "negative": 1.8}.get(label, 3.0)


def analyze_reviews(payload: dict[str, Any], lang: str | None = None) -> dict[str, Any]:
    ui_lang = _norm_lang(lang or payload.get("lang") or payload.get("language"))
    game = str(payload.get("game_name") or "Game")
    source = _norm_source(payload.get("source"))
    reviews = _reviews(payload)
    n = len(reviews)

    if n == 0:
        return {
            "game_name": game,
            "source": source,
            "lang": ui_lang,
            "summary": {
                "total_reviews": 0,
                "average_rating": 0,
                "positive": 0,
                "negative": 0,
                "neutral": 0,
                "languages": {},
            },
            "sentiments": {"positive": 0, "negative": 0, "neutral": 0},
            "categories": [],
            "trends": [],
            "top_issues": [],
            "top_praises": [],
            "recommendations": [],
            "health_score": 0,
            "summary_text": _t(ui_lang, "summary_ok", game=game, n=0, rating=0, pos=0),
            "visualizations": [],
            "methodology": _t(ui_lang, "methodology"),
            "export_text": f"=== {game} ===\nNo reviews.",
        }

    labels = [_classify_sentiment(r) for r in reviews]
    pos_n = labels.count("positive")
    neg_n = labels.count("negative")
    neu_n = labels.count("neutral")
    rated = [r["rating"] for r in reviews if r.get("rating") is not None]
    avg_rating = round(sum(rated) / len(rated), 2) if rated else round(
        sum(_sentiment_score_1_5(l, None) for l in labels) / n, 2
    )
    lang_counts = Counter(r["language"] or "en" for r in reviews)

    sentiments = {
        "positive": _pct(pos_n, n),
        "negative": _pct(neg_n, n),
        "neutral": _pct(neu_n, n),
    }

    # Categories
    cat_stats: dict[str, dict[str, Any]] = {}
    for key, meta in _CATEGORIES.items():
        hits = []
        for r, lab in zip(reviews, labels):
            rlang = "ru" if str(r.get("language")).startswith("ru") else "en"
            kws = meta.get(rlang) or meta["en"]
            if _word_hits(r["text"], kws):
                hits.append(_sentiment_score_1_5(lab, r.get("rating")))
        if not hits:
            continue
        label = meta["label_ru"] if ui_lang == "ru" else meta["label_en"]
        cat_stats[key] = {
            "name": label,
            "key": key,
            "sentiment": round(sum(hits) / len(hits), 2),
            "count": len(hits),
            "scores": hits,
        }

    # Trends by date
    by_date: dict[str, list[tuple[str, int | None]]] = defaultdict(list)
    for r, lab in zip(reviews, labels):
        d = r.get("date") or "unknown"
        by_date[d].append((lab, r.get("rating")))
    trends = []
    sorted_dates = sorted(k for k in by_date if k != "unknown")
    if "unknown" in by_date and not sorted_dates:
        sorted_dates = ["unknown"]
    elif "unknown" in by_date:
        sorted_dates.append("unknown")
    for d in sorted_dates:
        items = by_date[d]
        dn = len(items)
        dpos = sum(1 for lab, _ in items if lab == "positive")
        dneg = sum(1 for lab, _ in items if lab == "negative")
        dratings = [rt for _, rt in items if rt is not None]
        trends.append(
            {
                "date": d,
                "positive": _pct(dpos, dn),
                "negative": _pct(dneg, dn),
                "rating": round(sum(dratings) / len(dratings), 2) if dratings else None,
                "count": dn,
            }
        )

    # Category trend vs first/last half of dated reviews
    for key, st in cat_stats.items():
        # crude: compare average of first vs second half of scores
        scores = st["scores"]
        mid = max(1, len(scores) // 2)
        first = sum(scores[:mid]) / mid
        second = sum(scores[mid:]) / max(1, len(scores) - mid) if len(scores) > mid else first
        delta = second - first
        if delta >= 0.25:
            st["trend"] = _t(ui_lang, "trend_up")
        elif delta <= -0.25:
            st["trend"] = _t(ui_lang, "trend_down")
        else:
            st["trend"] = _t(ui_lang, "trend_stable")
        del st["scores"]

    categories = sorted(cat_stats.values(), key=lambda x: x["count"], reverse=True)

    # Issues / praises
    top_issues = []
    for pat in _ISSUE_PATTERNS:
        mentions = 0
        scores = []
        for r, lab in zip(reviews, labels):
            rlang = "ru" if str(r.get("language")).startswith("ru") else "en"
            kws = pat["ru_kw"] if rlang == "ru" else pat["en_kw"]
            if _word_hits(r["text"], kws) and lab != "positive":
                mentions += 1
                scores.append(_sentiment_score_1_5(lab, r.get("rating")))
            elif _word_hits(r["text"], kws) and (r.get("rating") or 5) <= 3:
                mentions += 1
                scores.append(_sentiment_score_1_5(lab, r.get("rating")))
        if mentions == 0:
            continue
        sev = "high" if mentions / n >= 0.25 or (scores and sum(scores) / len(scores) <= 2.2) else (
            "medium" if mentions / n >= 0.12 else "low"
        )
        top_issues.append(
            {
                "issue": pat["label_ru"] if ui_lang == "ru" else pat["label_en"],
                "mentions": mentions,
                "sentiment": round(sum(scores) / len(scores), 2) if scores else 2.0,
                "severity": sev,
                "id": pat["id"],
                "target": pat["target_ru"] if ui_lang == "ru" else pat["target_en"],
                "action": pat["action"],
                "recommendation": pat["rec_ru"] if ui_lang == "ru" else pat["rec_en"],
            }
        )
    top_issues.sort(key=lambda x: (-{"high": 3, "medium": 2, "low": 1}[x["severity"]], -x["mentions"]))
    top_issues = top_issues[:5]

    top_praises = []
    for pat in _PRAISE_PATTERNS:
        mentions = 0
        scores = []
        for r, lab in zip(reviews, labels):
            rlang = "ru" if str(r.get("language")).startswith("ru") else "en"
            kws = pat["ru_kw"] if rlang == "ru" else pat["en_kw"]
            if _word_hits(r["text"], kws) and (lab == "positive" or (r.get("rating") or 0) >= 4):
                mentions += 1
                scores.append(_sentiment_score_1_5(lab, r.get("rating")))
        if mentions == 0:
            continue
        top_praises.append(
            {
                "praise": pat["label_ru"] if ui_lang == "ru" else pat["label_en"],
                "mentions": mentions,
                "sentiment": round(sum(scores) / len(scores), 2) if scores else 4.5,
                "severity": "low",
                "id": pat["id"],
                "target": pat["target_ru"] if ui_lang == "ru" else pat["target_en"],
                "action": pat["action"],
                "recommendation": pat["rec_ru"] if ui_lang == "ru" else pat["rec_en"],
            }
        )
    top_praises.sort(key=lambda x: -x["mentions"])
    top_praises = top_praises[:5]

    recommendations = []
    seen = set()
    for item in top_issues + top_praises[:2]:
        key = (item.get("target"), item.get("action"))
        if key in seen:
            continue
        seen.add(key)
        recommendations.append(
            {
                "target": item["target"],
                "action": item["action"],
                "description": item["recommendation"],
            }
        )
    recommendations = recommendations[:6]

    health = 100
    health -= min(35, neg_n / n * 50)
    if avg_rating < 3.5:
        health -= min(25, (3.5 - avg_rating) * 15)
    health -= min(20, sum(1 for i in top_issues if i["severity"] == "high") * 8)
    health = int(max(0, min(100, round(health))))

    summary = {
        "total_reviews": n,
        "average_rating": avg_rating,
        "positive": pos_n,
        "negative": neg_n,
        "neutral": neu_n,
        "languages": dict(lang_counts),
        "source": source,
        "positive_rate": sentiments["positive"],
        "sentiment_score": round(sentiments["positive"] * 0.7 + (avg_rating / 5) * 30, 1),
    }

    if top_issues:
        summary_text = _t(ui_lang, "summary_issues", game=game, n=n, issues=len(top_issues))
    else:
        summary_text = _t(ui_lang, "summary_ok", game=game, n=n, rating=avg_rating, pos=sentiments["positive"])

    visualizations = [
        {
            "type": "bar_chart",
            "title": _t(ui_lang, "viz_sentiment"),
            "data": {
                "labels": ["Positive", "Neutral", "Negative"] if ui_lang != "ru" else ["Позитив", "Нейтрал", "Негатив"],
                "values": [sentiments["positive"], sentiments["neutral"], sentiments["negative"]],
            },
        },
        {
            "type": "line_chart",
            "title": _t(ui_lang, "viz_rating"),
            "data": {
                "labels": [t["date"] for t in trends if t.get("rating") is not None],
                "values": [t["rating"] for t in trends if t.get("rating") is not None],
            },
        },
        {
            "type": "bar_chart",
            "title": _t(ui_lang, "viz_categories"),
            "data": {
                "labels": [c["name"] for c in categories[:6]],
                "values": [c["count"] for c in categories[:6]],
            },
        },
    ]

    export_lines = [
        f"=== {game} ({source}) ===",
        summary_text,
        f"Avg rating: {avg_rating} | Pos {sentiments['positive']}% Neg {sentiments['negative']}%",
        "",
        "TOP ISSUES",
        *[f"- [{i['severity']}] {i['issue']} ({i['mentions']})" for i in top_issues],
        "",
        "TOP PRAISES",
        *[f"- {p['praise']} ({p['mentions']})" for p in top_praises],
        "",
        "RECOMMENDATIONS",
        *[f"- {r['target']}: {r['description']}" for r in recommendations],
    ]

    return {
        "game_name": game,
        "source": source,
        "lang": ui_lang,
        "summary": summary,
        "sentiments": sentiments,
        "categories": categories,
        "trends": trends,
        "top_issues": [{k: v for k, v in i.items() if k not in ("id", "target", "action", "recommendation")} for i in top_issues],
        "top_praises": [{k: v for k, v in p.items() if k not in ("id", "target", "action", "recommendation")} for p in top_praises],
        "recommendations": recommendations,
        "health_score": health,
        "summary_text": summary_text,
        "visualizations": visualizations,
        "methodology": _t(ui_lang, "methodology"),
        "export_text": "\n".join(export_lines),
    }


async def run_review_analysis(payload: dict[str, Any], lang: str | None = None) -> dict[str, Any]:
    lang = _norm_lang(lang or payload.get("lang"))
    base = analyze_reviews(payload, lang=lang)
    if settings.USE_MOCK_AI or not settings.OPENAI_API_KEY:
        return base
    try:
        return await _openai_enrich(payload, base, lang)
    except Exception:
        return base


async def _openai_enrich(payload: dict[str, Any], base: dict[str, Any], lang: str) -> dict[str, Any]:
    from app.services.openai_client import chat_completion

    lang_name = "Russian" if lang == "ru" else "English"
    compact = {
        "game_name": payload.get("game_name"),
        "summary": base.get("summary"),
        "top_issues": base.get("top_issues"),
        "top_praises": base.get("top_praises"),
        "sample_reviews": (_reviews(payload) or [])[:8],
    }
    prompt = f"""You are a senior game designer analyzing player reviews.
Write narrative fields in {lang_name}.
Improve summary_text and optionally add up to 3 extra_recommendations (target, action, description).
Do not invent metrics that contradict the summary numbers.

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
    extra = data.get("extra_recommendations")
    if isinstance(extra, list):
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
        out["recommendations"] = recs[:8]
    out["methodology"] = (
        "LLM-enriched review analysis"
        if lang != "ru"
        else "LLM-обогащённый анализ отзывов"
    )
    return out
