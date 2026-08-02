"""AI Localization — multi-language game text export."""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Dict, List

from app.config import get_settings

settings = get_settings()

SUPPORTED_LANGS = [
    "en", "ru", "es", "de", "fr", "it", "pt", "pl", "uk", "tr",
    "ja", "ko", "zh", "ar", "hi", "nl", "sv", "cs", "ro", "vi", "th", "id",
]

# Tiny offline glossary for mock mode
_MOCK_GLOSSARY = {
    "ru": {
        "start": "Начать",
        "settings": "Настройки",
        "quit": "Выход",
        "new game": "Новая игра",
        "continue": "Продолжить",
        "inventory": "Инвентарь",
        "quest": "Квест",
        "health": "Здоровье",
        "mana": "Мана",
        "attack": "Атака",
        "defend": "Защита",
        "save": "Сохранить",
        "load": "Загрузить",
        "hello": "Привет",
        "thank you": "Спасибо",
        "door": "Дверь",
        "key": "Ключ",
        "treasure": "Сокровище",
    },
    "es": {
        "start": "Empezar",
        "settings": "Ajustes",
        "quit": "Salir",
        "new game": "Nueva partida",
        "continue": "Continuar",
        "inventory": "Inventario",
        "quest": "Misión",
        "health": "Salud",
        "mana": "Maná",
        "attack": "Atacar",
        "defend": "Defender",
    },
    "de": {
        "start": "Start",
        "settings": "Einstellungen",
        "quit": "Beenden",
        "new game": "Neues Spiel",
        "continue": "Fortsetzen",
        "inventory": "Inventar",
        "quest": "Quest",
        "health": "Leben",
        "mana": "Mana",
    },
    "fr": {
        "start": "Commencer",
        "settings": "Paramètres",
        "quit": "Quitter",
        "new game": "Nouvelle partie",
        "continue": "Continuer",
        "inventory": "Inventaire",
        "quest": "Quête",
    },
    "ja": {
        "start": "スタート",
        "settings": "設定",
        "quit": "終了",
        "new game": "新しいゲーム",
        "continue": "つづきから",
        "inventory": "インベントリ",
        "quest": "クエスト",
    },
}


def _mock_translate(text: str, target: str) -> str:
    low = text.lower().strip()
    glossary = _MOCK_GLOSSARY.get(target, {})
    if low in glossary:
        return glossary[low]
    # Prefix marker so exporters still work offline
    return f"[{target}] {text}"


def _to_csv(translations: Dict[str, Dict[str, str]], keys: List[str], langs: List[str]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["key", *langs])
    for key in keys:
        row = [key] + [translations.get(lang, {}).get(key, "") for lang in langs]
        writer.writerow(row)
    return buf.getvalue()


async def localize(
    texts: Dict[str, str],
    source_lang: str = "en",
    target_langs: List[str] | None = None,
    export_format: str = "json",
) -> dict[str, Any]:
    target_langs = target_langs or ["ru", "es", "de", "fr", "ja"]
    target_langs = [t for t in target_langs if t in SUPPORTED_LANGS and t != source_lang]

    translations: Dict[str, Dict[str, str]] = {source_lang: dict(texts)}

    if settings.OPENAI_API_KEY and not settings.USE_MOCK_AI:
        try:
            translations.update(await _openai_localize(texts, source_lang, target_langs))
        except Exception:
            for lang in target_langs:
                translations[lang] = {k: _mock_translate(v, lang) for k, v in texts.items()}
    else:
        for lang in target_langs:
            translations[lang] = {k: _mock_translate(v, lang) for k, v in texts.items()}

    keys = list(texts.keys())
    export_payload: Any
    if export_format == "csv":
        export_payload = _to_csv(translations, keys, [source_lang, *target_langs])
    else:
        export_payload = translations

    return {
        "source_lang": source_lang,
        "target_langs": target_langs,
        "supported_langs": SUPPORTED_LANGS,
        "translations": translations,
        "export_format": export_format,
        "export": export_payload,
        "key_count": len(keys),
    }


async def _openai_localize(
    texts: Dict[str, str], source_lang: str, target_langs: List[str]
) -> Dict[str, Dict[str, str]]:
    from app.services.openai_client import get_openai_client

    client = get_openai_client()
    prompt = f"""Translate game UI/strings from {source_lang} to {target_langs}.
Preserve placeholders like {{name}}, %s, <color>.
Input JSON: {json.dumps(texts, ensure_ascii=False)}
Respond JSON: {{ "<lang>": {{ "<key>": "<translation>" }} }} for each target language."""

    resp = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)
