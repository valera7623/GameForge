"""AI Trailer Script — structured game trailer / promo video scripts."""

from __future__ import annotations

import json
from typing import Any

from app.config import get_settings

settings = get_settings()

TRAILER_TYPES = ("launch", "gameplay", "story", "teaser", "feature")
TONES = ("epic", "mysterious", "fun", "dramatic", "retro")

_VOICE_STYLE = {
    "en": {
        "epic": "deep, epic, dramatic",
        "mysterious": "hushed, intriguing, cinematic",
        "fun": "upbeat, energetic, playful",
        "dramatic": "emotional, intimate, measured",
        "retro": "pixel-era narrator, punchy and nostalgic",
    },
    "ru": {
        "epic": "глубокий, эпичный, драматичный",
        "mysterious": "приглушённый, интригующий, кинематографичный",
        "fun": "бодрый, энергичный, игривый",
        "dramatic": "эмоциональный, камерный, сдержанный",
        "retro": "пиксельный рассказчик, коротко и ностальгично",
    },
}

_COPY = {
    "en": {
        "title": "{name} — {kind} Trailer",
        "kinds": {
            "launch": "Launch",
            "gameplay": "Gameplay",
            "story": "Story",
            "teaser": "Teaser",
            "feature": "Feature",
        },
        "wishlist": "WISHLIST NOW",
        "coming": "coming {date}",
        "available": "available now",
        "methodology": "Template trailer structure with tone/duration + optional LLM polish",
        "music": {
            "epic": "Orchestral epic with heavy strings and brass. Tension builds to a climax.",
            "mysterious": "Sparse pads, dissonant strings, low pulses. Leave space for silence.",
            "fun": "Bright synth/orchestra hybrid, syncopated drums, playful stingers.",
            "dramatic": "Piano and strings, restrained then swelling for emotional peaks.",
            "retro": "Chiptune lead with modern low-end; arcade hits and bit-crushed whooshes.",
        },
        "ambient": "World atmosphere — wind, distant echoes, subtle room tone matching the genre.",
        "scenes": {
            "hook": {
                "title": "Hook",
                "visual": "Fade in from black. Iconic establishing shot of {name}'s world. Atmosphere first — mist, light, scale.",
                "action": "Slow push-in on a key silhouette or object. Minimal motion.",
                "vo": {
                    "epic": "Deep beneath the surface, an ancient power awakens...",
                    "mysterious": "Something waits where the maps end...",
                    "fun": "Ready for one more run?",
                    "dramatic": "Every choice leaves a mark...",
                    "retro": "Press start. The dungeon remembers.",
                },
                "sound": "Low rumble. Distant motif. Door / portal cue.",
            },
            "intro": {
                "title": "Intro",
                "visual": "Quick montage of environments from {genre}: corridors, vistas, hubs. 1–2s cuts.",
                "action": "Camera glides; show scale and tone of {name}.",
                "vo": {
                    "epic": "A world of endless adventure, built for the brave...",
                    "mysterious": "Rules shift. Trust nothing but your instincts...",
                    "fun": "Jump in, mess around, and find your style...",
                    "dramatic": "In {name}, survival is only the beginning...",
                    "retro": "Old-school challenge. Modern soul.",
                },
                "sound": "Score enters. Soft risers between cuts.",
            },
            "gameplay": {
                "title": "Gameplay",
                "visual": "Fast cuts of core loops: combat, exploration, systems. Highlight: {feature}.",
                "action": "Show readable player skill — dodge, commit, reward.",
                "vo": {
                    "epic": "Fight with skill, adapt to the unknown, and push deeper...",
                    "mysterious": "Learn the pattern… or become part of it...",
                    "fun": "Combo, crash, celebrate — then go again...",
                    "dramatic": "Every encounter asks who you choose to be...",
                    "retro": "Master the timing. Own the run.",
                },
                "overlay": "{feature_short}",
                "sound": "Gameplay SFX upfront; music ducks under hits.",
            },
            "feature": {
                "title": "Feature Spotlight",
                "visual": "Clean showcase of {feature}: UI, loot, or systems with readable close-ups.",
                "action": "Player unlocks / equips / discovers. Satisfying payoff beat.",
                "vo": {
                    "epic": "Forge your path with systems built for mastery...",
                    "mysterious": "Tools for those who look closer...",
                    "fun": "More toys. More chaos. More you...",
                    "dramatic": "Power comes with a price — spend it wisely...",
                    "retro": "Depth without the bloat.",
                },
                "overlay": "{feature_short}",
                "sound": "Bright discovery / level-up sting.",
            },
            "climax": {
                "title": "Climax",
                "visual": "Peak spectacle — boss, set-piece, or emotional beat. Camera energy spikes.",
                "action": "Tight cuts: threat → response → near-miss → triumph.",
                "vo": {
                    "epic": "Face the ultimate challenge… Will you survive?",
                    "mysterious": "When the truth surfaces — what will you do?",
                    "fun": "One last round. Make it legendary.",
                    "dramatic": "This is the moment everything changes.",
                    "retro": "Final stage. No continues.",
                },
                "overlay": "The Ultimate Test",
                "sound": "Full orchestra / beat drop. Signature enemy / impact hit.",
            },
            "cta": {
                "title": "Call to Action",
                "visual": "Logo card. Release info. Store / wishlist marks. Clean end slate.",
                "action": "Logo resolves. Hold for readability.",
                "vo": "{cta_line}",
                "overlay": "{cta_overlay}",
                "sound": "Triumphant final hit. Tail to silence.",
            },
        },
    },
    "ru": {
        "title": "{name} — {kind} трейлер",
        "kinds": {
            "launch": "Релизный",
            "gameplay": "Геймплейный",
            "story": "Сюжетный",
            "teaser": "Тизер",
            "feature": "Фича",
        },
        "wishlist": "В ВИШЛИСТ",
        "coming": "выход {date}",
        "available": "уже доступно",
        "methodology": "Шаблонная структура трейлера с тоном/длительностью + опциональная LLM-доработка",
        "music": {
            "epic": "Эпичный оркестр: струнные и медные. Нарастание к кульминации.",
            "mysterious": "Редкие пэды, диссонанс, низкий пульс. Место для тишины.",
            "fun": "Яркий синт/оркестр, синкопы, весёлые стингеры.",
            "dramatic": "Пианино и струнные: сдержанно, затем эмоциональный подъём.",
            "retro": "Чиптюн с современным низом; аркадные хиты и биткраш.",
        },
        "ambient": "Атмосфера мира — ветер, эхо, лёгкий room tone под жанр.",
        "scenes": {
            "hook": {
                "title": "Хук",
                "visual": "Фейд из чёрного. Знаковый кадр мира {name}. Сначала атмосфера — туман, свет, масштаб.",
                "action": "Медленный наезд на силуэт или ключевой объект. Минимум движения.",
                "vo": {
                    "epic": "Глубоко под поверхностью просыпается древняя сила...",
                    "mysterious": "Там, где кончаются карты, кто-то ждёт...",
                    "fun": "Готовы к ещё одному забегу?",
                    "dramatic": "Каждый выбор оставляет след...",
                    "retro": "Нажмите Start. Подземелье помнит.",
                },
                "sound": "Низкий гул. Далёкий мотив. Дверь / портал.",
            },
            "intro": {
                "title": "Интро",
                "visual": "Быстрый монтаж локаций жанра {genre}: коридоры, виды, хабы. Нарезка по 1–2 с.",
                "action": "Камера скользит; показать масштаб и тон {name}.",
                "vo": {
                    "epic": "Мир бесконечных приключений — для смелых...",
                    "mysterious": "Правила меняются. Верь только инстинкту...",
                    "fun": "Запрыгивай, экспериментируй, найди свой стиль...",
                    "dramatic": "В {name} выживание — только начало...",
                    "retro": "Олдскульный вызов. Современная душа.",
                },
                "sound": "Вступает саундтрек. Лёгкие райзеры между кадрами.",
            },
            "gameplay": {
                "title": "Геймплей",
                "visual": "Быстрые нарезки ядра: бой, исследование, системы. Акцент: {feature}.",
                "action": "Читаемый скилл игрока — уклон, удар, награда.",
                "vo": {
                    "epic": "Сражайся умело, адаптируйся и иди глубже...",
                    "mysterious": "Пойми паттерн… или стань его частью...",
                    "fun": "Комбо, хаос, праздник — и снова в бой...",
                    "dramatic": "Каждая встреча спрашивает, кем ты станешь...",
                    "retro": "Поймай тайминг. Забери забег.",
                },
                "overlay": "{feature_short}",
                "sound": "SFX геймплея вперёд; музыка под ударами приседает.",
            },
            "feature": {
                "title": "Фича",
                "visual": "Чистый показ {feature}: UI, лут или системы крупным планом.",
                "action": "Игрок открывает / надевает / находит. Кайфовый payoff.",
                "vo": {
                    "epic": "Ковай свой путь в системах, созданных для мастерства...",
                    "mysterious": "Инструменты для тех, кто смотрит внимательнее...",
                    "fun": "Больше игрушек. Больше хаоса. Больше тебя...",
                    "dramatic": "Сила имеет цену — трать её мудро...",
                    "retro": "Глубина без раздутости.",
                },
                "overlay": "{feature_short}",
                "sound": "Яркий стинг находки / левел-апа.",
            },
            "climax": {
                "title": "Кульминация",
                "visual": "Пик зрелища — босс, сетпис или эмоциональный удар. Энергия камеры растёт.",
                "action": "Плотные кадры: угроза → ответ → почти промах → триумф.",
                "vo": {
                    "epic": "Встреть главный вызов… Сможешь ли ты выжить?",
                    "mysterious": "Когда правда всплывёт — что ты сделаешь?",
                    "fun": "Последний раунд. Сделай его легендарным.",
                    "dramatic": "Миг, когда всё меняется.",
                    "retro": "Финал. Без continue.",
                },
                "overlay": "Главное испытание",
                "sound": "Полный оркестр / дроп. Фирменный удар врага.",
            },
            "cta": {
                "title": "Призыв к действию",
                "visual": "Карточка логотипа. Дата. Метки стора / вишлиста. Чистый end slate.",
                "action": "Логотип проявляется. Пауза для чтения.",
                "vo": "{cta_line}",
                "overlay": "{cta_overlay}",
                "sound": "Триумфальный финальный удар. Хвост в тишину.",
            },
        },
    },
}


def _norm_lang(lang: str | None) -> str:
    return "ru" if str(lang or "").lower().startswith("ru") else "en"


def _norm_type(t: str | None) -> str:
    v = str(t or "launch").lower().strip()
    return v if v in TRAILER_TYPES else "launch"


def _norm_tone(t: str | None) -> str:
    v = str(t or "epic").lower().strip()
    return v if v in TONES else "epic"


def _norm_duration(d: Any, trailer_type: str) -> int:
    try:
        n = int(d)
    except (TypeError, ValueError):
        n = 0
    defaults = {"teaser": 20, "gameplay": 45, "feature": 40, "story": 75, "launch": 60}
    if n < 10:
        n = defaults.get(trailer_type, 60)
    return max(15, min(180, n))


def _fmt_time(seconds: int) -> str:
    m, s = divmod(max(0, int(seconds)), 60)
    return f"{m}:{s:02d}"


def _beat_plan(trailer_type: str, duration: int) -> list[tuple[str, float]]:
    """Return ordered (beat_key, weight) summing ~1.0."""
    plans = {
        "teaser": [("hook", 0.45), ("climax", 0.35), ("cta", 0.20)],
        "gameplay": [("hook", 0.15), ("gameplay", 0.45), ("feature", 0.20), ("cta", 0.20)],
        "feature": [("hook", 0.15), ("feature", 0.45), ("gameplay", 0.20), ("cta", 0.20)],
        "story": [("hook", 0.20), ("intro", 0.25), ("feature", 0.20), ("climax", 0.20), ("cta", 0.15)],
        "launch": [
            ("hook", 0.12),
            ("intro", 0.15),
            ("gameplay", 0.28),
            ("feature", 0.18),
            ("climax", 0.15),
            ("cta", 0.12),
        ],
    }
    return plans.get(trailer_type, plans["launch"])


def _allocate(duration: int, weights: list[tuple[str, float]]) -> list[tuple[str, int]]:
    raw = [(k, max(3, int(round(duration * w)))) for k, w in weights]
    total = sum(s for _, s in raw)
    # Fix rounding drift on last beat
    if raw:
        diff = duration - total
        k, s = raw[-1]
        raw[-1] = (k, max(3, s + diff))
    return raw


def _features(game: dict[str, Any]) -> list[str]:
    raw = game.get("key_features") or []
    feats = [str(f).strip() for f in raw if str(f).strip()]
    if not feats:
        desc = str(game.get("description") or "").strip()
        if desc:
            feats = [desc[:80]]
        else:
            feats = ["Unique gameplay", "Memorable world"]
    return feats[:6]


def _cta_bits(game: dict[str, Any], lang: str, copy: dict[str, Any]) -> tuple[str, str]:
    name = str(game.get("game_name") or game.get("name") or "Game")
    date = str(game.get("release_date") or "").strip()
    wishlist = copy["wishlist"]
    if date:
        coming = copy["coming"].format(date=date)
        line = f"{name} — {coming}. {wishlist}."
        overlay = f"{name.upper()}\n{date}\n{wishlist}"
    else:
        line = f"{name} — {copy['available']}. {wishlist}."
        overlay = f"{name.upper()}\n{wishlist}"
    return line, overlay


def generate_trailer_script(game_data: dict[str, Any]) -> dict[str, Any]:
    lang = _norm_lang(game_data.get("lang") or game_data.get("language"))
    tone = _norm_tone(game_data.get("tone"))
    trailer_type = _norm_type(game_data.get("trailer_type"))
    duration = _norm_duration(game_data.get("duration"), trailer_type)
    copy = _COPY[lang]
    name = str(game_data.get("game_name") or game_data.get("name") or "Game")
    genre = str(game_data.get("genre") or "Adventure")
    feats = _features(game_data)
    cta_line, cta_overlay = _cta_bits(game_data, lang, copy)

    plan = _allocate(duration, _beat_plan(trailer_type, duration))
    scenes: list[dict[str, Any]] = []
    structure: dict[str, str] = {}
    overlays: list[dict[str, str]] = []
    t = 0
    feat_i = 0

    for idx, (beat, secs) in enumerate(plan, start=1):
        tpl = copy["scenes"][beat]
        feature = feats[feat_i % len(feats)]
        feat_i += 1
        feature_short = feature if len(feature) <= 40 else feature[:37] + "…"
        vo_src = tpl.get("vo", {})
        vo = vo_src.get(tone, next(iter(vo_src.values()), "")) if isinstance(vo_src, dict) else str(vo_src)
        vo = vo.format(name=name, cta_line=cta_line, feature=feature)
        visual = tpl["visual"].format(name=name, genre=genre, feature=feature)
        action = tpl["action"].format(name=name, feature=feature)
        overlay_tpl = tpl.get("overlay")
        overlay = None
        if overlay_tpl:
            overlay = overlay_tpl.format(
                feature_short=feature_short,
                cta_overlay=cta_overlay,
                name=name,
            )
            if beat == "cta":
                overlay = cta_overlay

        start, end = t, t + secs
        structure[beat if beat != "cta" else "call_to_action"] = f"{_fmt_time(start)}-{_fmt_time(end)}"
        if overlay:
            overlays.append({"time": _fmt_time(start), "text": overlay})

        scenes.append(
            {
                "scene_number": idx,
                "title": tpl["title"],
                "beat": beat,
                "start_seconds": start,
                "end_seconds": end,
                "timecode": f"{_fmt_time(start)} — {_fmt_time(end)}",
                "duration_seconds": secs,
                "visual": visual,
                "action": action,
                "voiceover": vo,
                "text_overlay": overlay,
                "sound": tpl["sound"],
            }
        )
        t = end

    full_vo = " ".join(s["voiceover"] for s in scenes if s.get("voiceover"))
    key_sounds = []
    for s in scenes:
        # short labels from first clause
        bit = str(s.get("sound") or "").split(".")[0].strip()
        if bit and bit not in key_sounds:
            key_sounds.append(bit)
        if len(key_sounds) >= 5:
            break

    kind = copy["kinds"].get(trailer_type, trailer_type.title())
    title = copy["title"].format(name=name, kind=kind)

    export_lines = [
        f"=== {title} ===",
        f"Duration: {duration}s | Type: {trailer_type} | Tone: {tone}",
        "",
        "STRUCTURE",
        *[f"- {k}: {v}" for k, v in structure.items()],
        "",
        "SCENES",
    ]
    for s in scenes:
        export_lines.extend(
            [
                f"\n[{s['timecode']}] {s['title']}",
                f"Visual: {s['visual']}",
                f"Action: {s['action']}",
                f"VO: {s['voiceover']}",
                f"Overlay: {s['text_overlay'] or '—'}",
                f"Sound: {s['sound']}",
            ]
        )
    export_lines.extend(
        [
            "",
            "FULL VOICEOVER",
            full_vo,
            "",
            "SOUND DESIGN",
            f"Music: {copy['music'][tone]}",
            f"Ambient: {copy['ambient']}",
        ]
    )

    return {
        "title": title,
        "game_name": name,
        "trailer_type": trailer_type,
        "tone": tone,
        "duration": duration,
        "lang": lang,
        "structure": structure,
        "scenes": scenes,
        "voiceover": {
            "full_text": full_vo,
            "voice_style": _VOICE_STYLE[lang][tone],
        },
        "text_overlays": overlays,
        "sound_design": {
            "music": copy["music"][tone],
            "key_sounds": key_sounds,
            "ambient": copy["ambient"],
        },
        "export_text": "\n".join(export_lines),
        "methodology": copy["methodology"],
        "platform": str(game_data.get("platform") or ""),
        "release_date": str(game_data.get("release_date") or ""),
        "urls": game_data.get("urls") if isinstance(game_data.get("urls"), dict) else {},
    }


async def run_trailer_script(game_data: dict[str, Any]) -> dict[str, Any]:
    base = generate_trailer_script(game_data)
    if settings.USE_MOCK_AI or not settings.OPENAI_API_KEY:
        return base
    try:
        return await _openai_polish(game_data, base)
    except Exception:
        return base


async def _openai_polish(game_data: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    from app.services.openai_client import chat_completion

    lang = base.get("lang") or "en"
    lang_name = "Russian" if lang == "ru" else "English"
    prompt = f"""You are a senior game trailer writer / marketing director.
Write ALL scene copy in {lang_name}. Keep the same number of scenes and approximate durations.
Improve visual, action, voiceover, text_overlay, and sound for each scene.
Also improve voiceover.full_text and sound_design.music if helpful.
Do not invent multiplayer or awards not in the brief.

Brief:
{json.dumps(game_data, ensure_ascii=False)[:4000]}

Draft scenes:
{json.dumps(base.get('scenes'), ensure_ascii=False)[:5000]}

Respond JSON only:
{{"scenes":[{{"scene_number":1,"visual":"...","action":"...","voiceover":"...","text_overlay":"...","sound":"..."}}],"voiceover_full_text":"...","music":"..."}}"""

    resp = await chat_completion(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    data = json.loads(resp.choices[0].message.content)
    out = dict(base)
    polished = data.get("scenes")
    if isinstance(polished, list) and polished:
        by_num = {int(s.get("scene_number", i + 1)): s for i, s in enumerate(polished) if isinstance(s, dict)}
        new_scenes = []
        for s in out["scenes"]:
            p = by_num.get(int(s["scene_number"]), {})
            merged = dict(s)
            for key in ("visual", "action", "voiceover", "text_overlay", "sound"):
                if isinstance(p.get(key), str) and p[key].strip():
                    merged[key] = p[key].strip()
            new_scenes.append(merged)
        out["scenes"] = new_scenes
        out["voiceover"] = dict(out.get("voiceover") or {})
        out["voiceover"]["full_text"] = " ".join(s["voiceover"] for s in new_scenes if s.get("voiceover"))
        overlays = []
        for s in new_scenes:
            if s.get("text_overlay"):
                overlays.append({"time": _fmt_time(s.get("start_seconds", 0)), "text": s["text_overlay"]})
        out["text_overlays"] = overlays
    if isinstance(data.get("voiceover_full_text"), str) and data["voiceover_full_text"].strip():
        out.setdefault("voiceover", {})["full_text"] = data["voiceover_full_text"].strip()
    if isinstance(data.get("music"), str) and data["music"].strip():
        out.setdefault("sound_design", {})["music"] = data["music"].strip()
    # Refresh export
    refreshed = generate_trailer_script({**game_data, "lang": lang})
    # Keep polished narrative fields but rebuild export from current out
    lines = [f"=== {out['title']} ===", "", "FULL VOICEOVER", out["voiceover"]["full_text"], "", "SCENES"]
    for s in out["scenes"]:
        lines.append(f"\n[{s.get('timecode')}] {s.get('title')}\nVO: {s.get('voiceover')}\nVisual: {s.get('visual')}")
    out["export_text"] = "\n".join(lines)
    out["methodology"] = (
        "LLM trailer script + structured beats"
        if lang != "ru"
        else "LLM-сценарий трейлера + структура битов"
    )
    # silence unused
    _ = refreshed
    return out
