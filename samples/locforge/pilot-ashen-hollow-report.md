# LocForge demo pilot — Ashen Hollow
Date: 2026-08-09
Source: samples/locforge/ashen-hollow-en.csv
Mode: mock localize (USE_MOCK_AI)

## Before
- EN-only CSV (key,source)
- 68 keys · 273 source words
- No glossary, no length QA, no engine-specific export

## After
- Target langs: ru, es, de
- Glossary locked: Mira, Torren, Ashen Hollow, Ashen Blade (9 glossary hits)
- Length QA: 39 unique keys flagged too_long (22 UI/HUD/hint)
- Exports available: json, csv, unity_csv, unity_json, godot_csv
- Pseudo-locale available for layout stress-test

## Runtime
- Mock pass: <1s for this pack
- Live OpenAI: expect minutes for similar size (not measured in this run)

## Replace when
A live indie sends CSV + grants permission to name the game on /locforge.
