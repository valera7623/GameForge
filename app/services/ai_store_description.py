"""AI Store Description — marketing copy for Steam / App Store / Google Play / Epic."""

from __future__ import annotations

import json
import re
from typing import Any

from app.config import get_settings

settings = get_settings()

PLATFORMS = ("steam", "appstore", "googleplay", "epic")
TONES = ("epic", "mysterious", "fun", "serious", "retro")

_CTA = {
    "en": {
        "epic": "Begin your legendary journey — wishlist and play now!",
        "mysterious": "Uncover what waits in the dark. Download today.",
        "fun": "Jump in and start the adventure!",
        "serious": "Experience the full release — available now.",
        "retro": "Press start. The dungeon awaits.",
    },
    "ru": {
        "epic": "Начните легендарное путешествие — добавьте в вишлист и играйте!",
        "mysterious": "Узнайте, что скрыто во тьме. Скачайте сегодня.",
        "fun": "Прыгайте в игру и начните приключение!",
        "serious": "Полный релиз уже доступен.",
        "retro": "Нажмите Start. Подземелье ждёт.",
    },
}

_OPENERS = {
    "en": {
        "epic": "Embark on a legendary journey in {name}.",
        "mysterious": "Something stirs beneath the surface of {name}.",
        "fun": "Grab your gear and dive into {name}!",
        "serious": "{name} is a carefully crafted {genre} experience.",
        "retro": "Old-school thrills meet modern design in {name}.",
    },
    "ru": {
        "epic": "Отправьтесь в легендарное путешествие в мире {name}.",
        "mysterious": "Что-то шевелится под поверхностью в {name}.",
        "fun": "Хватайте снаряжение и ныряйте в {name}!",
        "serious": "{name} — тщательно проработанный {genre}.",
        "retro": "Олдскульный вайб и современный дизайн в {name}.",
    },
}


def _norm_lang(lang: str | None) -> str:
    code = str(lang or "en").lower().split("-")[0]
    return code if code in ("en", "ru", "es", "fr", "de", "ja", "pt", "zh") else "en"


def _norm_platform(platform: str | None) -> str:
    p = str(platform or "steam").lower().replace(" ", "").replace("_", "")
    aliases = {
        "appstore": "appstore",
        "ios": "appstore",
        "apple": "appstore",
        "googleplay": "googleplay",
        "google": "googleplay",
        "android": "googleplay",
        "epic": "epic",
        "epicgames": "epic",
        "steam": "steam",
    }
    return aliases.get(p, "steam")


def _norm_tone(tone: str | None) -> str:
    t = str(tone or "epic").lower()
    return t if t in TONES else "epic"


def _clip(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0]
    return (cut or text[: limit - 1]).rstrip(".,;:") + "…"


def _features(game: dict[str, Any]) -> list[str]:
    raw = game.get("key_features") or []
    feats = [str(f).strip() for f in raw if str(f).strip()]
    usp = str(game.get("usp") or "").strip()
    if usp and usp not in feats:
        feats.insert(0, usp)
    # Ensure at least a few
    genre = str(game.get("genre") or "Adventure")
    defaults = {
        "en": [
            f"Engaging {genre} gameplay",
            "Polished controls and feedback",
            "Replayable challenges",
            "Distinctive art and audio",
        ],
        "ru": [
            f"Увлекательный геймплей в жанре {genre}",
            "Отточенное управление и отклик",
            "Высокая реиграбельность",
            "Запоминающийся арт и звук",
        ],
    }
    lang = _norm_lang(game.get("language") or game.get("lang"))
    base = defaults.get(lang, defaults["en"])
    while len(feats) < 4:
        nxt = base[len(feats) % len(base)]
        if nxt not in feats:
            feats.append(nxt)
        else:
            feats.append(f"{genre} highlight #{len(feats)+1}")
    return feats[:8]


def _tags(game: dict[str, Any]) -> list[str]:
    genre = str(game.get("genre") or "Adventure")
    platform = str(game.get("platform") or "PC")
    audience = str(game.get("target_audience") or "casual")
    parts = re.split(r"[,/|&]+", genre)
    tags = [p.strip().title() for p in parts if p.strip()]
    extras = {
        "hardcore": ["Challenging", "Skill-Based"],
        "casual": ["Family Friendly", "Easy to Learn"],
        "family": ["Family Friendly", "Co-op"],
    }.get(audience.lower(), ["Indie"])
    tags.extend(extras)
    if "pc" in platform.lower():
        tags.append("Singleplayer")
    if "mobile" in platform.lower():
        tags.extend(["Mobile", "Touch Controls"])
    # Dedup preserve order
    seen = set()
    out = []
    for t in tags:
        k = t.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(t)
    return out[:12]


def _short_desc(game: dict[str, Any], tone: str, lang: str, limit: int) -> str:
    name = str(game.get("game_name") or game.get("name") or "Your Game")
    desc = str(game.get("description") or "").strip()
    usp = str(game.get("usp") or "").strip()
    opener_map = _OPENERS.get(lang, _OPENERS["en"])
    opener = opener_map.get(tone, opener_map["epic"]).format(
        name=name, genre=str(game.get("genre") or "game")
    )
    body = desc or usp or opener
    if desc and usp and usp.lower() not in desc.lower():
        body = f"{_clip(desc, max(40, limit // 2))} {usp}"
    elif not desc:
        body = f"{opener} {usp}".strip()
    return _clip(body, limit)


def _long_desc(game: dict[str, Any], tone: str, lang: str, feats: list[str]) -> str:
    name = str(game.get("game_name") or game.get("name") or "Your Game")
    genre = str(game.get("genre") or "Adventure")
    usp = str(game.get("usp") or "").strip()
    desc = str(game.get("description") or "").strip()
    audience = str(game.get("target_audience") or "players")
    opener_map = _OPENERS.get(lang, _OPENERS["en"])
    opener = opener_map.get(tone, opener_map["epic"]).format(name=name, genre=genre)

    if lang == "ru":
        mid = desc or f"{name} — это {genre} с акцентом на {usp or 'уникальный геймплей'}."
        feat_block = "\n".join(f"• {f}" for f in feats[:6])
        closing = {
            "epic": "Сможете ли вы пройти путь до конца?",
            "mysterious": "Что вы найдёте, если копнёте глубже?",
            "fun": "Готовы к новому забегу?",
            "serious": "Создано для игроков, которые ценят глубину и мастерство.",
            "retro": "Классика жанра — в новой упаковке.",
        }.get(tone, "Начните играть сегодня.")
        return (
            f"{opener}\n\n{mid}\n\n"
            f"Ключевые особенности:\n{feat_block}\n\n"
            f"Для аудитории: {audience}.\n\n{closing}"
        )

    mid = desc or f"{name} is a {genre} built around {usp or 'memorableable gameplay loops'}."
    feat_block = "\n".join(f"• {f}" for f in feats[:6])
    closing = {
        "epic": "Will you rise to the challenge?",
        "mysterious": "What will you uncover if you dig deeper?",
        "fun": "Ready for another run?",
        "serious": "Built for players who value depth and craft.",
        "retro": "Classic genre thrills — with a modern polish.",
    }.get(tone, "Start playing today.")
    return (
        f"{opener}\n\n{mid}\n\n"
        f"Key features:\n{feat_block}\n\n"
        f"Made for {audience} players.\n\n{closing}"
    )


def _steam_html(name: str, long_desc: str, feats: list[str], cta: str, lang: str) -> str:
    about = "Об игре" if lang == "ru" else "About This Game"
    features = "Особенности" if lang == "ru" else "Features"
    items = "".join(f"<li>{_escape_html(f)}</li>" for f in feats[:8])
    paras = "".join(f"<p>{_escape_html(p)}</p>" for p in long_desc.split("\n\n") if p.strip() and not p.strip().startswith("•") and "Key features" not in p and "Ключевые" not in p)
    return (
        f"<h2>{about}</h2>\n"
        f"{paras}\n"
        f"<h2>{features}</h2>\n"
        f"<ul>{items}</ul>\n"
        f"<p><strong>{_escape_html(cta)}</strong></p>\n"
    )


def _escape_html(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _platform_bundle(
    game: dict[str, Any],
    tone: str,
    lang: str,
    feats: list[str],
    tags: list[str],
    cta: str,
) -> dict[str, Any]:
    # Character limits roughly matching store guidelines
    limits = {
        "steam": (300, 8000),
        "appstore": (170, 4000),
        "googleplay": (80, 4000),
        "epic": (120, 2000),
    }
    out: dict[str, Any] = {}
    for plat, (short_lim, _long_lim) in limits.items():
        short = _short_desc(game, tone, lang, short_lim)
        long = _long_desc(game, tone, lang, feats)
        out[plat] = {
            "short_description": short,
            "long_description": long,
            "features": feats[:6],
            "tags": tags,
            "call_to_action": cta,
        }
    return out


def generate_store_description(game_data: dict[str, Any]) -> dict[str, Any]:
    lang = _norm_lang(game_data.get("language") or game_data.get("lang"))
    tone = _norm_tone(game_data.get("tone"))
    target = _norm_platform(game_data.get("target_platform"))
    game = dict(game_data)
    game["language"] = lang

    feats = _features(game)
    tags = _tags(game)
    cta_map = _CTA.get(lang, _CTA["en"])
    cta = cta_map.get(tone, cta_map["epic"])

    platform_specific = _platform_bundle(game, tone, lang, feats, tags, cta)
    primary = platform_specific[target]
    short = primary["short_description"]
    long = primary["long_description"]
    name = str(game.get("game_name") or game.get("name") or "Game")

    steam_html = _steam_html(name, long, feats, cta, lang)

    return {
        "short_description": short,
        "long_description": long,
        "key_features": feats,
        "tags": tags,
        "call_to_action": cta,
        "target_platform": target,
        "language": lang,
        "tone": tone,
        "platform_specific": platform_specific,
        "steam_description": steam_html,
        "appstore_description": platform_specific["appstore"]["long_description"],
        "googleplay_description": platform_specific["googleplay"]["long_description"],
        "epic_description": platform_specific["epic"]["long_description"],
        "export_text": _export_text(name, short, long, feats, tags, cta, target, lang),
        "methodology": "Template marketing copy with tone/platform limits"
        if lang != "ru"
        else "Шаблонный маркетинг-копирайтинг с учётом тона и лимитов платформ",
    }


def _export_text(
    name: str,
    short: str,
    long: str,
    feats: list[str],
    tags: list[str],
    cta: str,
    platform: str,
    lang: str,
) -> str:
    if lang == "ru":
        return (
            f"=== {name} ({platform}) ===\n\n"
            f"Краткое описание:\n{short}\n\n"
            f"Полное описание:\n{long}\n\n"
            f"Особенности:\n" + "\n".join(f"- {f}" for f in feats) + "\n\n"
            f"Теги: {', '.join(tags)}\n\n"
            f"CTA: {cta}\n"
        )
    return (
        f"=== {name} ({platform}) ===\n\n"
        f"Short description:\n{short}\n\n"
        f"Long description:\n{long}\n\n"
        f"Key features:\n" + "\n".join(f"- {f}" for f in feats) + "\n\n"
        f"Tags: {', '.join(tags)}\n\n"
        f"CTA: {cta}\n"
    )


async def run_store_description(game_data: dict[str, Any]) -> dict[str, Any]:
    base = generate_store_description(game_data)
    if settings.USE_MOCK_AI or not settings.OPENAI_API_KEY:
        return base
    try:
        return await _openai_polish(game_data, base)
    except Exception:
        return base


async def _openai_polish(game_data: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    from app.services.openai_client import chat_completion

    lang = base.get("language") or "en"
    lang_name = {
        "en": "English",
        "ru": "Russian",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "ja": "Japanese",
        "pt": "Portuguese",
        "zh": "Chinese",
    }.get(lang, "English")
    platform = base.get("target_platform") or "steam"
    tone = base.get("tone") or "epic"

    prompt = f"""You are a senior game store marketer.
Write ALL marketing copy in {lang_name}.
Tone: {tone}. Primary store: {platform}.
Improve short_description, long_description, key_features (4-8), tags (5-10), call_to_action.
Respect approximate limits: Steam short ~300 chars, App Store short ~170, Google Play short ~80.
Do not invent false claims (multiplayer, reviews) not present in the input.

Game input:
{json.dumps(game_data, ensure_ascii=False)[:5000]}

Draft:
{json.dumps({k: base[k] for k in ('short_description','long_description','key_features','tags','call_to_action')}, ensure_ascii=False)[:4000]}

Respond JSON only:
{{"short_description":"...","long_description":"...","key_features":["..."],"tags":["..."],"call_to_action":"..."}}"""

    resp = await chat_completion(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content)
    out = dict(base)
    for key in ("short_description", "long_description", "call_to_action"):
        if isinstance(data.get(key), str) and data[key].strip():
            out[key] = data[key].strip()
    if isinstance(data.get("key_features"), list) and data["key_features"]:
        out["key_features"] = [str(x) for x in data["key_features"] if str(x).strip()][:8]
    if isinstance(data.get("tags"), list) and data["tags"]:
        out["tags"] = [str(x) for x in data["tags"] if str(x).strip()][:12]

    # Rebuild platform bundles from polished core
    game = dict(game_data)
    game["language"] = lang
    feats = out["key_features"]
    tags = out["tags"]
    cta = out["call_to_action"]
    out["platform_specific"] = _platform_bundle(game, tone, lang, feats, tags, cta)
    # Keep primary short/long from polish, sync into target platform
    target = out["target_platform"]
    out["platform_specific"][target]["short_description"] = out["short_description"]
    out["platform_specific"][target]["long_description"] = out["long_description"]
    out["platform_specific"][target]["features"] = feats
    out["platform_specific"][target]["call_to_action"] = cta
    name = str(game.get("game_name") or "Game")
    out["steam_description"] = _steam_html(name, out["long_description"], feats, cta, lang)
    out["appstore_description"] = out["platform_specific"]["appstore"]["long_description"]
    out["googleplay_description"] = out["platform_specific"]["googleplay"]["long_description"]
    out["epic_description"] = out["platform_specific"]["epic"]["long_description"]
    out["export_text"] = _export_text(
        name, out["short_description"], out["long_description"], feats, tags, cta, target, lang
    )
    out["methodology"] = (
        "LLM store copy + platform formatting"
        if lang != "ru"
        else "LLM-копирайтинг для магазинов + форматирование платформ"
    )
    return out
