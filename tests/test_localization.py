"""Tests for AI Localization — glossary + CSV parse + mock translate."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.schemas import LocalizationRequest, ProjectGlossaryUpdate
from app.services import ai_localization
from app.services.ai_localization import (
    LocalizationCsvError,
    _apply_glossary,
    _mock_translate,
    normalize_glossary,
    parse_source_csv,
)


def test_normalize_glossary_strips_empty():
    raw = {
        "HeroName": {"ru": "Герой", "es": "  "},
        "  ": {"ru": "x"},
        "Start": {"RU": "Начать", "": "nope"},
    }
    cleaned = normalize_glossary(raw)
    assert cleaned == {"HeroName": {"ru": "Герой"}, "Start": {"ru": "Начать"}}


def test_normalize_glossary_none():
    assert normalize_glossary(None) is None
    assert normalize_glossary({}) is None


def test_parse_source_csv_basic():
    """T1: key,source with quoted commas."""
    csv_text = 'key,source\nui.start,Start game\nquest.intro,"Welcome, traveler."\n'
    parsed = parse_source_csv(csv_text)
    assert parsed["key_count"] == 2
    assert parsed["texts"]["ui.start"] == "Start game"
    assert parsed["texts"]["quest.intro"] == "Welcome, traveler."
    assert parsed["delimiter"] == ","


def test_parse_source_csv_key_en_comma():
    """T1: key,en header (Unity-style English column)."""
    parsed = parse_source_csv("key,en\nui.ok,OK\nui.cancel,Cancel\n")
    assert parsed["delimiter"] == ","
    assert parsed["texts"] == {"ui.ok": "OK", "ui.cancel": "Cancel"}


def test_parse_source_csv_key_source_semicolon():
    """T1: key;source with semicolon delimiter."""
    parsed = parse_source_csv("key;source\nui.start;Start\nquest.intro;Hello")
    assert parsed["delimiter"] == ";"
    assert parsed["texts"]["ui.start"] == "Start"
    assert parsed["texts"]["quest.intro"] == "Hello"


def test_parse_source_csv_semicolon_and_bom():
    """T1: BOM + key;en."""
    csv_text = "\ufeffkey;en\na;hello\nb;world"
    parsed = parse_source_csv(csv_text)
    assert parsed["key_count"] == 2
    assert parsed["texts"]["a"] == "hello"
    assert parsed["delimiter"] == ";"


def test_parse_source_csv_duplicate_key():
    """T4 (unit): duplicate key raises LocalizationCsvError."""
    with pytest.raises(LocalizationCsvError, match="csv_duplicate_key:a"):
        parse_source_csv("key,source\na,1\na,2")


def test_parse_source_csv_empty_raises():
    """T4 (unit): empty CSV raises."""
    with pytest.raises(LocalizationCsvError, match="empty_csv"):
        parse_source_csv("")
    with pytest.raises(LocalizationCsvError, match="empty_csv"):
        parse_source_csv("   \n  \n")


def test_parse_source_csv_empty_key_warning():
    parsed = parse_source_csv("key,source\n,skip\nok,yes")
    assert parsed["key_count"] == 1
    assert len(parsed["warnings"]) == 1


def test_mock_translate_uses_user_glossary_before_builtin():
    """T2: user glossary wins over builtin mock glossary."""
    glossary = {"start": {"ru": "Поехали"}}
    assert _mock_translate("Start", "ru", glossary) == "Поехали"
    assert _mock_translate("start", "ru", glossary) == "Поехали"


def test_mock_translate_falls_back_to_builtin():
    assert _mock_translate("inventory", "ru", None) == "Инвентарь"
    assert _mock_translate("Unknown Label", "ru", None) == "[ru] Unknown Label"


def test_apply_glossary_overwrites_translations():
    texts = {"npc.name": "HeroName", "ui.ok": "OK"}
    translations = {
        "ru": {"npc.name": "[ru] HeroName", "ui.ok": "[ru] OK"},
        "es": {"npc.name": "[es] HeroName", "ui.ok": "[es] OK"},
    }
    glossary = {"HeroName": {"ru": "Герой", "es": "Héroe"}}
    hits = _apply_glossary(texts, translations, glossary)
    assert hits == 2
    assert translations["ru"]["npc.name"] == "Герой"
    assert translations["es"]["npc.name"] == "Héroe"
    assert translations["ru"]["ui.ok"] == "[ru] OK"


@pytest.mark.asyncio
async def test_localize_mock_applies_glossary():
    """T2: localize() in mock mode applies glossary to translations."""
    result = await ai_localization.localize(
        texts={"npc.name": "HeroName", "ui.start": "Start"},
        source_lang="en",
        target_langs=["ru", "es"],
        export_format="json",
        glossary={"HeroName": {"ru": "Герой", "es": "Héroe"}},
        include_qa=False,
        include_pseudo=False,
    )
    assert result["glossary_terms"] == 1
    assert result["glossary_hits"] >= 2
    assert result["translations"]["ru"]["npc.name"] == "Герой"
    assert result["translations"]["es"]["npc.name"] == "Héroe"
    assert result["translations"]["ru"]["ui.start"]


def test_localization_request_glossary_optional():
    """T3: glossary is optional on LocalizationRequest."""
    req = LocalizationRequest(texts={"a": "A"}, target_langs=["ru"])
    assert req.glossary is None


def test_localization_request_glossary_normalized():
    """T3: glossary lang codes lowercased; empty translations dropped."""
    req = LocalizationRequest(
        texts={"a": "HeroName"},
        target_langs=["ru"],
        glossary={"HeroName": {"RU": "Герой", "es": ""}},
    )
    assert req.glossary == {"HeroName": {"ru": "Герой"}}


def test_project_glossary_update_normalizes():
    body = ProjectGlossaryUpdate(glossary={"Hero": {"RU": "Герой", "es": ""}})
    assert body.glossary == {"Hero": {"ru": "Герой"}}


def test_localization_request_empty_texts_allowed():
    req = LocalizationRequest(texts={}, target_langs=["ru"])
    assert req.texts == {}


@pytest.mark.asyncio
async def test_localization_api_with_glossary(client: AsyncClient):
    """T2+T3: API accepts glossary and mock apply returns forced translation."""
    email = "loc_glossary@example.com"
    password = "password1234"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Loc"},
    )
    assert reg.status_code == 201, reg.text
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200

    resp = await client.post(
        "/api/v1/localization",
        json={
            "texts": {"npc.name": "HeroName", "ui.ok": "OK"},
            "source_lang": "en",
            "target_langs": ["ru"],
            "export_format": "json",
            "glossary": {"HeroName": {"ru": "Герой"}},
            "include_qa": False,
            "include_pseudo": False,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tool"] == "localization"
    assert body["status"] == "completed"
    assert body["output_data"]["translations"]["ru"]["npc.name"] == "Герой"
    assert body["output_data"]["glossary_terms"] == 1
    assert body["output_data"]["glossary_hits"] >= 1


@pytest.mark.asyncio
async def test_localization_api_glossary_validation(client: AsyncClient):
    """T3: request with glossary passes validation (200); malformed glossary types → 422."""
    email = "loc_gloss_val@example.com"
    password = "password1234"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Val"},
    )
    assert reg.status_code == 201, reg.text
    await client.post("/api/v1/auth/login", json={"email": email, "password": password})

    ok = await client.post(
        "/api/v1/localization",
        json={
            "texts": {"a": "A"},
            "target_langs": ["ru"],
            "glossary": {"A": {"RU": "А"}},
            "include_qa": False,
            "include_pseudo": False,
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["output_data"]["translations"]["ru"]["a"] == "А"

    bad = await client.post(
        "/api/v1/localization",
        json={
            "texts": {"a": "A"},
            "target_langs": ["ru"],
            "glossary": ["not", "a", "dict"],
        },
    )
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_parse_csv_api(client: AsyncClient):
    email = "loc_csv@example.com"
    password = "password1234"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "CSV"},
    )
    assert reg.status_code == 201, reg.text
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200

    csv_bytes = b"key,source\nui.start,Start\nnpc.name,HeroName\n"
    resp = await client.post(
        "/api/v1/localization/parse-csv",
        files={"file": ("strings.csv", csv_bytes, "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["key_count"] == 2
    assert data["texts"]["ui.start"] == "Start"


@pytest.mark.asyncio
async def test_parse_csv_api_duplicate_and_empty_return_400(client: AsyncClient):
    """T4: duplicate key / empty CSV → HTTP 400."""
    email = "loc_csv_err@example.com"
    password = "password1234"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Err"},
    )
    assert reg.status_code == 201, reg.text
    await client.post("/api/v1/auth/login", json={"email": email, "password": password})

    dup = await client.post(
        "/api/v1/localization/parse-csv",
        files={"file": ("dup.csv", b"key,source\na,1\na,2\n", "text/csv")},
    )
    assert dup.status_code == 400, dup.text
    assert "Duplicate key" in dup.json()["detail"]

    empty = await client.post(
        "/api/v1/localization/parse-csv",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert empty.status_code == 400, empty.text
    assert "empty" in empty.json()["detail"].lower()

    header_only = await client.post(
        "/api/v1/localization/parse-csv",
        files={"file": ("hdr.csv", b"key,source\n", "text/csv")},
    )
    assert header_only.status_code == 400, header_only.text


@pytest.mark.asyncio
async def test_project_glossary_api(client: AsyncClient):
    email = "loc_proj_gloss@example.com"
    password = "password1234"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "PG"},
    )
    assert reg.status_code == 201, reg.text
    await client.post("/api/v1/auth/login", json={"email": email, "password": password})

    created = await client.post("/api/v1/projects", json={"name": "Loc Game", "engine": "unity"})
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    put = await client.put(
        f"/api/v1/projects/{project_id}/glossary",
        json={"glossary": {"HeroName": {"ru": "Герой", "es": "Héroe"}}},
    )
    assert put.status_code == 200, put.text
    assert put.json()["glossary"]["HeroName"]["ru"] == "Герой"

    got = await client.get(f"/api/v1/projects/{project_id}/glossary")
    assert got.status_code == 200
    assert got.json()["glossary"]["HeroName"]["es"] == "Héroe"


def test_pseudo_localize_preserves_placeholders():
    from app.services.ai_localization import build_pseudo, pseudo_localize_text

    out = pseudo_localize_text("Hello {name}!")
    assert "{name}" in out
    assert out.startswith("[") and out.endswith("]")
    assert "Hello" not in out  # accented
    assert len(out) > len("Hello {name}!")

    batch = build_pseudo({"a": "Hi", "b": "Go %s"})
    assert "%s" in batch["b"]
    assert batch["a"].startswith("[")


def test_length_qa_flags_too_long_and_short():
    from app.services.ai_localization import run_length_qa

    texts = {"short": "OK", "long": "Hello"}
    translations = {
        "en": dict(texts),
        "ru": {
            "short": "Очень длинный перевод строки",  # too long vs "OK"
            "long": "Х",  # too short vs "Hello"
        },
    }
    issues = run_length_qa(texts, translations, "en")
    flags = {(i["key"], i["flag"]) for i in issues}
    assert ("short", "too_long") in flags
    assert ("long", "too_short") in flags


def test_unity_and_godot_exports():
    from app.services.ai_localization import build_export

    translations = {
        "en": {"ui.start": "Start"},
        "ru": {"ui.start": "Старт"},
    }
    keys = ["ui.start"]
    langs = ["en", "ru"]

    unity_csv = build_export("unity_csv", translations, keys, langs)
    assert "Key" in unity_csv and "Id" in unity_csv
    assert "English(en)" in unity_csv and "Russian(ru)" in unity_csv
    assert "Start" in unity_csv

    unity_json = build_export("unity_json", translations, keys, langs)
    assert unity_json["format"] == "unity_string_tables"
    assert unity_json["tables"]["ru"]["entries"][0]["value"] == "Старт"

    godot = build_export("godot_csv", translations, keys, langs)
    assert godot.splitlines()[0].startswith("keys,")
    assert "ui.start" in godot


@pytest.mark.asyncio
async def test_localize_includes_qa_and_pseudo():
    result = await ai_localization.localize(
        texts={"ui.start": "Start"},
        source_lang="en",
        target_langs=["ru"],
        export_format="godot_csv",
        include_qa=True,
        include_pseudo=True,
    )
    assert "pseudo" in result
    assert result["pseudo"]["ui.start"].startswith("[")
    assert "qa_issues" in result
    assert result["export_format"] == "godot_csv"
    assert isinstance(result["export"], str)
    assert result["export"].startswith("keys,")
