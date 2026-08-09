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


Glossary = Dict[str, Dict[str, str]]

_SOURCE_HEADERS = frozenset({"source", "en", "text", "value", "string", "english", "src"})
_KEY_HEADERS = frozenset({"key", "id", "name", "string_id", "stringid"})


class LocalizationCsvError(ValueError):
    """Raised when source CSV cannot be parsed into localization texts."""


def parse_source_csv(content: str | bytes) -> dict[str, Any]:
    """Parse key/source CSV into texts dict (mirrors frontend loc-csv.js)."""
    if content is None:
        raise LocalizationCsvError("empty_csv")
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")
    raw = str(content).replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    if not raw.strip():
        raise LocalizationCsvError("empty_csv")

    # Sniff delimiter from first non-empty line
    first_line = next((ln for ln in raw.split("\n") if ln.strip()), "")
    delim = ";" if first_line.count(";") > first_line.count(",") else ","

    reader = csv.reader(io.StringIO(raw), delimiter=delim)
    try:
        headers = next(reader)
    except StopIteration as exc:
        raise LocalizationCsvError("empty_csv") from exc

    headers_norm = [h.strip().lower() for h in headers]
    if not any(headers_norm):
        raise LocalizationCsvError("csv_need_header_and_row")

    key_idx = next((i for i, h in enumerate(headers_norm) if h in _KEY_HEADERS), -1)
    source_idx = next((i for i, h in enumerate(headers_norm) if h in _SOURCE_HEADERS), -1)
    if key_idx < 0 and source_idx < 0 and len(headers_norm) >= 2:
        key_idx, source_idx = 0, 1
    else:
        if key_idx < 0:
            raise LocalizationCsvError("csv_no_key_column")
        if source_idx < 0:
            source_idx = next((i for i in range(len(headers_norm)) if i != key_idx), -1)
        if source_idx < 0:
            raise LocalizationCsvError("csv_no_source_column")

    texts: Dict[str, str] = {}
    warnings: List[str] = []
    seen: Dict[str, int] = {}
    for row_num, cols in enumerate(reader, start=2):
        if not cols or all(not str(c).strip() for c in cols):
            continue
        key = (cols[key_idx] if key_idx < len(cols) else "").strip()
        value = (cols[source_idx] if source_idx < len(cols) else "").strip()
        if not key:
            warnings.append(f"row_{row_num}_empty_key")
            continue
        if key in seen:
            raise LocalizationCsvError(f"csv_duplicate_key:{key}")
        seen[key] = row_num
        texts[key] = value

    if not texts:
        raise LocalizationCsvError("csv_no_rows")

    return {
        "texts": texts,
        "key_count": len(texts),
        "warnings": warnings,
        "delimiter": delim,
    }


def normalize_glossary(glossary: Glossary | None) -> Glossary | None:
    if not glossary:
        return None
    cleaned: Glossary = {}
    for term, langs in glossary.items():
        term_key = (term or "").strip()
        if not term_key or not isinstance(langs, dict):
            continue
        lang_map = {
            str(code).strip().lower(): str(val)
            for code, val in langs.items()
            if str(code).strip() and str(val).strip()
        }
        if lang_map:
            cleaned[term_key] = lang_map
    return cleaned or None


# Back-compat alias
_normalize_glossary = normalize_glossary


def _glossary_index(glossary: Glossary | None) -> Dict[str, Dict[str, str]]:
    """Lowercased source term → { lang → translation }."""
    if not glossary:
        return {}
    return {term.lower().strip(): langs for term, langs in glossary.items() if term.strip()}


def _resolve_glossary_term(text: str, target: str, glossary: Glossary | None) -> str | None:
    langs = _glossary_index(glossary).get(text.lower().strip())
    if not langs:
        return None
    val = langs.get(target)
    return val if val else None


def _apply_glossary(
    texts: Dict[str, str],
    translations: Dict[str, Dict[str, str]],
    glossary: Glossary | None,
) -> int:
    """Force exact glossary hits onto translations. Returns how many values overwritten."""
    index = _glossary_index(glossary)
    if not index:
        return 0
    applied = 0
    for key, source in texts.items():
        langs = index.get(source.lower().strip())
        if not langs:
            continue
        for lang, translated in langs.items():
            if lang in translations and translated:
                translations[lang][key] = translated
                applied += 1
    return applied


def _mock_translate(text: str, target: str, glossary: Glossary | None = None) -> str:
    hit = _resolve_glossary_term(text, target, glossary)
    if hit is not None:
        return hit
    low = text.lower().strip()
    built_in = _MOCK_GLOSSARY.get(target, {})
    if low in built_in:
        return built_in[low]
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


# Accent map for pseudo-localization (visual expansion + diacritics).
_PSEUDO_MAP = str.maketrans({
    "a": "à", "A": "À", "b": "ƀ", "B": "Ɓ", "c": "ç", "C": "Ç",
    "d": "đ", "D": "Đ", "e": "é", "E": "É", "f": "ƒ", "F": "Ƒ",
    "g": "ĝ", "G": "Ĝ", "h": "ĥ", "H": "Ĥ", "i": "í", "I": "Í",
    "j": "ĵ", "J": "Ĵ", "k": "ķ", "K": "Ķ", "l": "ł", "L": "Ł",
    "m": "ɱ", "M": "Ɱ", "n": "ñ", "N": "Ñ", "o": "ö", "O": "Ö",
    "p": "þ", "P": "Þ", "q": "ʠ", "Q": "Ɋ", "r": "ř", "R": "Ř",
    "s": "š", "S": "Š", "t": "ţ", "T": "Ţ", "u": "ū", "U": "Ū",
    "v": "ṽ", "V": "Ṽ", "w": "ŵ", "W": "Ŵ", "x": "χ", "X": "Χ",
    "y": "ý", "Y": "Ý", "z": "ž", "Z": "Ž",
})


def pseudo_localize_text(text: str, pad_ratio: float = 0.3) -> str:
    """Wrap + accent + pad ~30% so UI overflow shows up before real translation."""
    if not text:
        return "[]"
    # Preserve placeholders like {name}, %s, %d, <tags>
    parts: List[str] = []
    i = 0
    buf = ""
    while i < len(text):
        ch = text[i]
        if ch == "{":
            if buf:
                parts.append(("t", buf))
                buf = ""
            end = text.find("}", i)
            if end == -1:
                buf += ch
                i += 1
                continue
            parts.append(("p", text[i : end + 1]))
            i = end + 1
            continue
        if ch == "<":
            if buf:
                parts.append(("t", buf))
                buf = ""
            end = text.find(">", i)
            if end == -1:
                buf += ch
                i += 1
                continue
            parts.append(("p", text[i : end + 1]))
            i = end + 1
            continue
        if ch == "%" and i + 1 < len(text):
            if buf:
                parts.append(("t", buf))
                buf = ""
            # %s %d %1$s style
            j = i + 1
            while j < len(text) and (text[j].isdigit() or text[j] in "$.-+#"):
                j += 1
            if j < len(text) and text[j].isalpha():
                parts.append(("p", text[i : j + 1]))
                i = j + 1
                continue
        buf += ch
        i += 1
    if buf:
        parts.append(("t", buf))

    out = []
    for kind, chunk in parts:
        if kind == "p":
            out.append(chunk)
        else:
            out.append(chunk.translate(_PSEUDO_MAP))
    accented = "".join(out)
    pad_n = max(1, int(len(text) * pad_ratio))
    pad = ("·" * pad_n)
    return f"[{accented}{pad}]"


def build_pseudo(texts: Dict[str, str]) -> Dict[str, str]:
    return {k: pseudo_localize_text(v) for k, v in texts.items()}


def run_length_qa(
    texts: Dict[str, str],
    translations: Dict[str, Dict[str, str]],
    source_lang: str,
    min_ratio: float = 0.4,
    max_ratio: float = 1.2,
) -> List[dict[str, Any]]:
    """Flag translations that are much shorter/longer than the source string."""
    issues: List[dict[str, Any]] = []
    for key, source in texts.items():
        src_len = len(source)
        if src_len == 0:
            continue
        for lang, block in translations.items():
            if lang == source_lang:
                continue
            trans = block.get(key, "")
            if not trans:
                continue
            ratio = len(trans) / src_len
            flag = None
            if ratio > max_ratio:
                flag = "too_long"
            elif ratio < min_ratio:
                flag = "too_short"
            if flag:
                issues.append({
                    "key": key,
                    "lang": lang,
                    "flag": flag,
                    "source_len": src_len,
                    "trans_len": len(trans),
                    "ratio": round(ratio, 2),
                    "source": source,
                    "translation": trans,
                })
    return issues


_UNITY_LANG_NAMES = {
    "en": "English", "ru": "Russian", "es": "Spanish", "de": "German",
    "fr": "French", "it": "Italian", "pt": "Portuguese", "pl": "Polish",
    "uk": "Ukrainian", "tr": "Turkish", "ja": "Japanese", "ko": "Korean",
    "zh": "Chinese", "ar": "Arabic", "hi": "Hindi", "nl": "Dutch",
    "sv": "Swedish", "cs": "Czech", "ro": "Romanian", "vi": "Vietnamese",
    "th": "Thai", "id": "Indonesian",
}


def _unity_col(lang: str) -> str:
    name = _UNITY_LANG_NAMES.get(lang, lang.upper())
    return f"{name}({lang})"


def _to_unity_csv(
    translations: Dict[str, Dict[str, str]], keys: List[str], langs: List[str]
) -> str:
    """Unity Localization Package string-table CSV (Key, Id, Locale columns)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Key", "Id", *[_unity_col(lang) for lang in langs]])
    for i, key in enumerate(keys):
        row = [key, str(i)] + [translations.get(lang, {}).get(key, "") for lang in langs]
        writer.writerow(row)
    return buf.getvalue()


def _to_unity_json(
    translations: Dict[str, Dict[str, str]], keys: List[str], langs: List[str]
) -> dict[str, Any]:
    """Unity-friendly string tables: one table per locale."""
    tables = {}
    for lang in langs:
        entries = []
        for i, key in enumerate(keys):
            entries.append({
                "key": key,
                "id": i,
                "value": translations.get(lang, {}).get(key, ""),
            })
        tables[lang] = {
            "locale": lang,
            "localeDisplayName": _UNITY_LANG_NAMES.get(lang, lang),
            "entries": entries,
        }
    return {"format": "unity_string_tables", "tables": tables}


def _to_godot_csv(
    translations: Dict[str, Dict[str, str]], keys: List[str], langs: List[str]
) -> str:
    """Godot translation CSV: keys,<locale…>."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["keys", *langs])
    for key in keys:
        row = [key] + [translations.get(lang, {}).get(key, "") for lang in langs]
        writer.writerow(row)
    return buf.getvalue()


def build_export(
    export_format: str,
    translations: Dict[str, Dict[str, str]],
    keys: List[str],
    langs: List[str],
) -> Any:
    if export_format == "csv":
        return _to_csv(translations, keys, langs)
    if export_format == "unity_csv":
        return _to_unity_csv(translations, keys, langs)
    if export_format == "unity_json":
        return _to_unity_json(translations, keys, langs)
    if export_format == "godot_csv":
        return _to_godot_csv(translations, keys, langs)
    return translations


async def localize(
    texts: Dict[str, str],
    source_lang: str = "en",
    target_langs: List[str] | None = None,
    export_format: str = "json",
    glossary: Glossary | None = None,
    include_qa: bool = True,
    include_pseudo: bool = True,
) -> dict[str, Any]:
    target_langs = target_langs or ["ru", "es", "de", "fr", "ja"]
    target_langs = [t for t in target_langs if t in SUPPORTED_LANGS and t != source_lang]
    glossary = _normalize_glossary(glossary)

    translations: Dict[str, Dict[str, str]] = {source_lang: dict(texts)}

    if settings.USE_MOCK_AI:
        for lang in target_langs:
            translations[lang] = {
                k: _mock_translate(v, lang, glossary) for k, v in texts.items()
            }
    else:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is required when USE_MOCK_AI=false")
        translations.update(
            await _openai_localize(texts, source_lang, target_langs, glossary)
        )

    glossary_hits = _apply_glossary(texts, translations, glossary)

    keys = list(texts.keys())
    all_langs = [source_lang, *target_langs]
    export_payload = build_export(export_format, translations, keys, all_langs)

    result: dict[str, Any] = {
        "source_lang": source_lang,
        "target_langs": target_langs,
        "supported_langs": SUPPORTED_LANGS,
        "translations": translations,
        "export_format": export_format,
        "export": export_payload,
        "key_count": len(keys),
        "glossary_terms": len(glossary) if glossary else 0,
        "glossary_hits": glossary_hits,
    }
    if include_pseudo:
        result["pseudo"] = build_pseudo(texts)
    if include_qa:
        issues = run_length_qa(texts, translations, source_lang)
        result["qa_issues"] = issues
        result["qa_issue_count"] = len(issues)
    return result


async def _openai_localize(
    texts: Dict[str, str],
    source_lang: str,
    target_langs: List[str],
    glossary: Glossary | None = None,
) -> Dict[str, Dict[str, str]]:
    from app.services.openai_client import chat_completion
    langs = ", ".join(target_langs)
    keys = list(texts.keys())
    glossary_block = ""
    if glossary:
        glossary_block = f"""
6. Glossary — use these translations EXACTLY for the listed source terms (whole-string match).
   Do not invent variants, synonyms, or alternate spellings for glossary terms.
{json.dumps(glossary, ensure_ascii=False, indent=2)}
"""
    prompt = f"""You are a professional game localization translator.

Task: translate the UI/game strings below from source language "{source_lang}" into each of: {langs}.

Rules:
1. Keep every input key unchanged; translate only the string values.
2. Preserve placeholders and markup exactly as written, including:
   - curly braces: {{name}}, {{count}}, {{0}}
   - printf: %s, %d, %1$s
   - tags: <color>, </color>, <b>, </b>, [b], [/b]
3. Keep tone suitable for games (UI labels short and natural; dialogue may be more expressive).
4. Do not add explanations, transliterate brand/proper names only when customary in the target language.
5. Return ONLY valid JSON (no markdown).
{glossary_block}
Output schema (one object; top-level keys are language codes):
{{
  "{target_langs[0] if target_langs else "ru"}": {{
    "{keys[0] if keys else "example.key"}": "translated string"
  }}
}}

Include every language in [{langs}] and every key in {json.dumps(keys, ensure_ascii=False)}.

Source strings ({source_lang}):
{json.dumps(texts, ensure_ascii=False, indent=2)}
"""

    resp = await chat_completion(
        model=settings.OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You translate game localization files. "
                    "Reply with a single JSON object: language code → { key → translation }."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    raw = json.loads(resp.choices[0].message.content or "{}")
    return _normalize_localization_payload(raw, texts, target_langs)


def _normalize_localization_payload(
    raw: Dict[str, Any], texts: Dict[str, str], target_langs: List[str]
) -> Dict[str, Dict[str, str]]:
    """Accept common LLM shapes and guarantee lang → key → str."""
    out: Dict[str, Dict[str, str]] = {}
    # Some models wrap as {"translations": {...}} or {"data": {...}}
    if len(raw) == 1:
        only = next(iter(raw.values()))
        if isinstance(only, dict) and any(lang in only for lang in target_langs):
            raw = only  # type: ignore[assignment]

    for lang in target_langs:
        block = raw.get(lang)
        if not isinstance(block, dict):
            # case-insensitive lang key
            block = next(
                (v for k, v in raw.items() if str(k).lower() == lang.lower() and isinstance(v, dict)),
                {},
            )
        cleaned: Dict[str, str] = {}
        for key in texts:
            val = block.get(key) if isinstance(block, dict) else None
            cleaned[key] = str(val) if val is not None else texts[key]
        out[lang] = cleaned
    return out
