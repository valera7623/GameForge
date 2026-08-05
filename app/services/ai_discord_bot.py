"""AI Discord Bot — config helpers, moderation, commands, community analytics."""

from __future__ import annotations

import base64
import hashlib
import json
import random
import re
from collections import Counter
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings

settings = get_settings()

_SPAM_RE = re.compile(r"(.)\1{6,}|https?://\S+|discord\.gg/\S+|free\s*nitro|@everyone", re.I)
_TOXIC = {
    "en": ("idiot", "stupid", "kill yourself", "kys", "trash player", "noob trash", "shut up"),
    "ru": ("идиот", "тупой", "убейся", "мусор", "заткнись", "дебил"),
}
_ADS = {
    "en": ("buy cheap", "promo code", "subscribe to my", "onlyfans", "crypto giveaway"),
    "ru": ("купи дешев", "промокод", "подпишись на мой", "крипто раздач", "бесплатный нитро"),
}

DEFAULT_COMMANDS = [
    {"command": "help", "description": "List all commands", "usage": "!help", "category": "info", "response": ""},
    {"command": "rules", "description": "Server rules", "usage": "!rules", "category": "info", "response": "Be kind. No spam. No spoilers without tags. Have fun."},
    {"command": "game", "description": "Game info", "usage": "!game", "category": "info", "response": ""},
    {"command": "stats", "description": "Community stats", "usage": "!stats", "category": "info", "response": ""},
    {"command": "about", "description": "About this bot", "usage": "!about", "category": "info", "response": "Powered by GameForge AI Discord Bot."},
    {"command": "roll", "description": "Roll dice (d6/d20)", "usage": "!roll d20", "category": "fun", "response": ""},
    {"command": "flip", "description": "Coin flip", "usage": "!flip", "category": "fun", "response": ""},
    {"command": "8ball", "description": "Magic 8-ball", "usage": "!8ball <question>", "category": "fun", "response": ""},
    {"command": "patch", "description": "Latest patch notes", "usage": "!patch", "category": "game", "response": ""},
    {"command": "event", "description": "Current event", "usage": "!event", "category": "game", "response": ""},
    {"command": "roadmap", "description": "Roadmap", "usage": "!roadmap", "category": "game", "response": ""},
    {"command": "feedback", "description": "How to send feedback", "usage": "!feedback", "category": "game", "response": "Share feedback with the team via the pinned channel or GameForge Review Analyzer."},
]

_MSG = {
    "en": {
        "methodology": "Rule-based Discord moderation + command simulator + community message analytics",
        "status_ready": "Configured — token saved (gateway connect is managed separately)",
        "status_missing": "Not configured — add guild ID and bot token",
        "status_connected": "Marked connected",
        "welcome_default": "Welcome {user} to the {game} community!",
        "mod_clean": "Message looks clean",
        "mod_spam": "Spam / invite / link flood detected",
        "mod_toxic": "Toxic language detected",
        "mod_ads": "Promotional / scam patterns detected",
        "action_delete": "delete",
        "action_warn": "warn",
        "action_timeout": "timeout",
        "action_none": "none",
        "summary": "{bot}: {n} sample messages · moderated {mod}% · sentiment pos {pos}%",
    },
    "ru": {
        "methodology": "Правила модерации Discord + симулятор команд + аналитика сообщений комьюнити",
        "status_ready": "Настроен — токен сохранён (подключение gateway отдельно)",
        "status_missing": "Не настроен — укажите guild ID и токен бота",
        "status_connected": "Отмечен как подключённый",
        "welcome_default": "Добро пожаловать, {user}, в комьюнити {game}!",
        "mod_clean": "Сообщение чистое",
        "mod_spam": "Обнаружен спам / инвайт / флуд ссылками",
        "mod_toxic": "Обнаружена токсичность",
        "mod_ads": "Обнаружена реклама / скамовые паттерны",
        "action_delete": "delete",
        "action_warn": "warn",
        "action_timeout": "timeout",
        "action_none": "none",
        "summary": "{bot}: сообщений {n} · модерация {mod}% · позитив {pos}%",
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


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_bot_token(raw: str) -> str:
    return _fernet().encrypt(raw.strip().encode()).decode()


def decrypt_bot_token(enc: str | None) -> str | None:
    if not enc:
        return None
    try:
        return _fernet().decrypt(enc.encode()).decode()
    except (InvalidToken, Exception):
        return None


def mask_token(last4: str | None) -> str | None:
    if not last4:
        return None
    return f"••••••••{last4}"


def default_moderation() -> dict[str, Any]:
    return {
        "enabled": True,
        "auto_delete": True,
        "warn_threshold": 3,
        "timeout_duration": 300,
        "spam_threshold": 5,
        "spam_window": 10,
    }


def default_welcome(game: str = "Game") -> dict[str, Any]:
    return {
        "enabled": True,
        "message": f"Welcome {{user}} to the {game} community! 🎮",
        "channel_id": "",
    }


def default_analytics() -> dict[str, Any]:
    return {"enabled": True, "report_frequency": "weekly", "channels": []}


def default_stats() -> dict[str, Any]:
    return {
        "messages": 0,
        "moderation_actions": 0,
        "commands_run": 0,
        "warnings": 0,
        "servers": 1,
        "channels": 1,
        "users": 0,
    }


def moderate_message(content: str, *, lang: str = "en", moderation: dict[str, Any] | None = None) -> dict[str, Any]:
    lang = _norm_lang(lang)
    mod = {**default_moderation(), **(moderation or {})}
    text = (content or "").strip()
    flags: list[str] = []
    reasons: list[str] = []

    if not text:
        return {
            "flagged": False,
            "action": _t(lang, "action_none"),
            "reasons": [],
            "score": 0,
            "description": _t(lang, "mod_clean"),
        }

    low = text.lower()
    score = 0

    if _SPAM_RE.search(text) or len(text) > 800:
        flags.append("spam")
        reasons.append(_t(lang, "mod_spam"))
        score += 40

    toxic_words = _TOXIC["ru"] if re.search(r"[А-Яа-яЁё]", text) else _TOXIC["en"]
    if any(w in low for w in toxic_words):
        flags.append("toxicity")
        reasons.append(_t(lang, "mod_toxic"))
        score += 45

    ad_words = _ADS["ru"] if re.search(r"[А-Яа-яЁё]", text) else _ADS["en"]
    if any(w in low for w in ad_words):
        flags.append("ads")
        reasons.append(_t(lang, "mod_ads"))
        score += 35

    flagged = score >= 30 and bool(mod.get("enabled", True))
    if not flagged:
        action = _t(lang, "action_none")
        desc = _t(lang, "mod_clean")
    elif "toxicity" in flags and score >= 60:
        action = _t(lang, "action_timeout") if mod.get("auto_delete") else _t(lang, "action_warn")
        desc = reasons[0]
    elif mod.get("auto_delete"):
        action = _t(lang, "action_delete")
        desc = reasons[0] if reasons else _t(lang, "mod_spam")
    else:
        action = _t(lang, "action_warn")
        desc = reasons[0] if reasons else _t(lang, "mod_spam")

    return {
        "flagged": flagged,
        "action": action,
        "reasons": reasons,
        "flags": flags,
        "score": min(100, score),
        "description": desc,
    }


def render_welcome(template: str, *, user: str, game: str, lang: str = "en") -> str:
    tpl = (template or "").strip() or _t(lang, "welcome_default")
    return tpl.replace("{user}", user).replace("{game}", game)


_EIGHT_BALL = {
    "en": [
        "It is certain.",
        "Without a doubt.",
        "Ask again later.",
        "Cannot predict now.",
        "Don't count on it.",
        "My sources say no.",
        "Outlook good.",
        "Very doubtful.",
    ],
    "ru": [
        "Бесспорно.",
        "Без сомнений.",
        "Спроси позже.",
        "Сейчас не ясно.",
        "Не стоит на это рассчитывать.",
        "Мои источники говорят «нет».",
        "Перспективы хорошие.",
        "Очень сомнительно.",
    ],
}


def run_builtin_command(
    command: str,
    args: str = "",
    *,
    lang: str = "en",
    game_info: dict[str, Any] | None = None,
    custom_response: str | None = None,
    prefix: str = "!",
    commands_catalog: list[dict[str, Any]] | None = None,
    stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lang = _norm_lang(lang)
    cmd = str(command or "").lower().lstrip("/!").strip()
    info = game_info or {}
    game = str(info.get("name") or info.get("game_name") or "Game")
    stats = stats or default_stats()

    if custom_response and custom_response.strip() and cmd not in ("help", "roll", "flip", "8ball", "stats"):
        return {"command": cmd, "ok": True, "response": custom_response.strip()}

    if cmd == "help":
        catalog = commands_catalog or DEFAULT_COMMANDS
        lines = [f"{prefix}{c['command']} — {c.get('description') or ''}" for c in catalog if c.get("is_active", True)]
        return {"command": cmd, "ok": True, "response": "\n".join(lines) or "No commands."}

    if cmd == "game":
        desc = str(info.get("description") or ("Информация об игре скоро появится." if lang == "ru" else "Game info coming soon."))
        return {"command": cmd, "ok": True, "response": f"**{game}**\n{desc}"}

    if cmd == "stats":
        body = (
            f"Messages: {stats.get('messages', 0)} · Moderation: {stats.get('moderation_actions', 0)} · "
            f"Commands: {stats.get('commands_run', 0)} · Warnings: {stats.get('warnings', 0)}"
        )
        if lang == "ru":
            body = (
                f"Сообщения: {stats.get('messages', 0)} · Модерация: {stats.get('moderation_actions', 0)} · "
                f"Команды: {stats.get('commands_run', 0)} · Варны: {stats.get('warnings', 0)}"
            )
        return {"command": cmd, "ok": True, "response": body}

    if cmd == "about":
        return {
            "command": cmd,
            "ok": True,
            "response": "GameForge AI Discord Bot — moderation, FAQ commands, and community analytics.",
        }

    if cmd == "rules":
        return {
            "command": cmd,
            "ok": True,
            "response": custom_response
            or ("Будьте вежливы. Без спама. Без спойлеров без тегов." if lang == "ru" else "Be kind. No spam. Tag spoilers."),
        }

    if cmd == "roll":
        sides = 20
        m = re.search(r"d(\d+)", args.lower()) or re.search(r"d(\d+)", cmd)
        if m:
            sides = max(2, min(1000, int(m.group(1))))
        elif args.strip().isdigit():
            sides = max(2, min(1000, int(args.strip())))
        val = random.randint(1, sides)
        return {"command": cmd, "ok": True, "response": f"🎲 d{sides} → **{val}**"}

    if cmd == "flip":
        face = random.choice(["Heads", "Tails"] if lang != "ru" else ["Орёл", "Решка"])
        return {"command": cmd, "ok": True, "response": f"🪙 {face}"}

    if cmd == "8ball":
        ans = random.choice(_EIGHT_BALL[lang])
        q = args.strip() or ("?" if lang != "ru" else "?")
        return {"command": cmd, "ok": True, "response": f"🎱 {q}\n→ {ans}"}

    if cmd == "patch":
        return {
            "command": cmd,
            "ok": True,
            "response": str(info.get("patch") or ("Патчноуты скоро." if lang == "ru" else "Patch notes coming soon.")),
        }

    if cmd == "event":
        return {
            "command": cmd,
            "ok": True,
            "response": str(info.get("event") or ("Сейчас нет активных ивентов." if lang == "ru" else "No active events.")),
        }

    if cmd == "roadmap":
        return {
            "command": cmd,
            "ok": True,
            "response": str(info.get("roadmap") or ("Roadmap скоро." if lang == "ru" else "Roadmap coming soon.")),
        }

    if cmd == "feedback":
        return {
            "command": cmd,
            "ok": True,
            "response": custom_response
            or (
                "Отправьте отзыв в канал feedback или через AI Review Analyzer."
                if lang == "ru"
                else "Send feedback in #feedback or via AI Review Analyzer."
            ),
        }

    if custom_response and custom_response.strip():
        return {"command": cmd, "ok": True, "response": custom_response.strip()}

    return {
        "command": cmd,
        "ok": False,
        "response": f"Unknown command: {prefix}{cmd}" if lang != "ru" else f"Неизвестная команда: {prefix}{cmd}",
    }


def analyze_community(
    payload: dict[str, Any],
    *,
    lang: str | None = None,
) -> dict[str, Any]:
    lang = _norm_lang(lang or payload.get("lang"))
    bot_name = str(payload.get("bot_name") or "Discord Bot")
    messages = payload.get("messages") or []
    if not isinstance(messages, list):
        messages = []
    texts = []
    for m in messages:
        if isinstance(m, str):
            texts.append(m)
        elif isinstance(m, dict):
            t = str(m.get("content") or m.get("text") or "").strip()
            if t:
                texts.append(t)

    n = len(texts)
    mod_hits = 0
    pos = neg = neu = 0
    actions: Counter = Counter()
    for text in texts:
        result = moderate_message(text, lang=lang, moderation=payload.get("moderation"))
        if result["flagged"]:
            mod_hits += 1
            actions[result["action"]] += 1
            neg += 1
        else:
            low = text.lower()
            if any(w in low for w in ("love", "great", "thanks", "круто", "спасибо", "люблю", "класс")):
                pos += 1
            elif any(w in low for w in ("hate", "bad", "плохо", "бесит")):
                neg += 1
            else:
                neu += 1

    def pct(x: int) -> float:
        return round(100.0 * x / n, 1) if n else 0.0

    summary_text = _t(
        lang,
        "summary",
        bot=bot_name,
        n=n,
        mod=pct(mod_hits),
        pos=pct(pos),
    )

    activity = [max(1, n - i * max(1, n // 5)) for i in range(5)] if n else [0, 0, 0, 0, 0]
    visualizations = [
        {
            "type": "bar_chart",
            "title": "User activity" if lang != "ru" else "Активность",
            "data": {
                "labels": ["W1", "W2", "W3", "W4", "W5"] if lang != "ru" else ["Н1", "Н2", "Н3", "Н4", "Н5"],
                "values": list(reversed(activity)),
            },
        },
        {
            "type": "bar_chart",
            "title": "Sentiment" if lang != "ru" else "Тональность",
            "data": {
                "labels": ["Positive", "Neutral", "Negative"] if lang != "ru" else ["Позитив", "Нейтрал", "Негатив"],
                "values": [pct(pos), pct(neu), pct(neg)],
            },
        },
    ]

    recommendations = []
    if pct(mod_hits) >= 20:
        recommendations.append(
            {
                "target": "Moderation",
                "action": "tighten_filters",
                "description": (
                    "Ужесточите авто-удаление спама и добавьте slowmode в горячие каналы."
                    if lang == "ru"
                    else "Tighten auto-delete and enable slowmode on hot channels."
                ),
            }
        )
    if pct(pos) >= 50:
        recommendations.append(
            {
                "target": "Community",
                "action": "amplify",
                "description": (
                    "Закрепите позитивные моменты и запускайте еженедельные ивенты."
                    if lang == "ru"
                    else "Pin positive highlights and run weekly community events."
                ),
            }
        )
    if not recommendations:
        recommendations.append(
            {
                "target": "Onboarding",
                "action": "welcome",
                "description": (
                    "Включите welcome-сообщение с !help и правилами."
                    if lang == "ru"
                    else "Enable a welcome message that points to !help and rules."
                ),
            }
        )

    return {
        "bot_name": bot_name,
        "lang": lang,
        "summary": {
            "total_messages": n,
            "moderated": mod_hits,
            "moderated_rate": pct(mod_hits),
            "positive": pct(pos),
            "neutral": pct(neu),
            "negative": pct(neg),
            "actions": dict(actions),
        },
        "sentiment": {"positive": pct(pos), "neutral": pct(neu), "negative": pct(neg)},
        "recommendations": recommendations,
        "visualizations": visualizations,
        "summary_text": summary_text,
        "methodology": _t(lang, "methodology"),
        "export_text": summary_text + "\n\n" + json.dumps({"actions": dict(actions)}, ensure_ascii=False, indent=2),
    }


def config_public_dict(row: Any, *, lang: str = "en") -> dict[str, Any]:
    has_token = bool(getattr(row, "bot_token_enc", None))
    ready = bool(getattr(row, "guild_id", None)) and has_token
    connected = bool(getattr(row, "is_connected", False))
    if connected:
        status_label = _t(lang, "status_connected")
        status = "online"
    elif ready:
        status_label = _t(lang, "status_ready")
        status = "ready"
    else:
        status_label = _t(lang, "status_missing")
        status = "offline"

    return {
        "id": str(row.id),
        "bot_name": row.bot_name,
        "guild_id": row.guild_id,
        "channel_id": row.channel_id,
        "prefix": row.prefix,
        "token_masked": mask_token(row.token_last4),
        "has_token": has_token,
        "moderation_enabled": row.moderation_enabled,
        "welcome_enabled": row.welcome_enabled,
        "analytics_enabled": row.analytics_enabled,
        "moderation": row.moderation or default_moderation(),
        "welcome": row.welcome or default_welcome(),
        "analytics": row.analytics or default_analytics(),
        "game_info": row.game_info or {},
        "is_connected": connected,
        "status": status,
        "status_label": status_label,
        "stats": row.stats or default_stats(),
        "updated_at": row.updated_at.isoformat() if getattr(row, "updated_at", None) else None,
    }
