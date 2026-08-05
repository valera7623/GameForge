# Tools

GameForge ships **fourteen** AI tools. With `USE_MOCK_AI=true` they run without paid keys; with `USE_MOCK_AI=false` they call external providers (OpenAI / ProxyAPI and optional services).

Marketing pages: `/tools/<slug>` (EN) and `/ru/tools/<slug>` (RU). In-app editors: `https://gameforge.website/<slug>` after login.

## Level Designer

- **Input:** natural-language level brief (optional project)
- **Output:** tilemap JSON + canvas preview
- **API:** `POST /api/v1/level-designer`

## Quest Generator

- **Input:** quest / story prompt
- **Output:** quest structure, dialogues, branches as JSON
- **API:** `POST /api/v1/quest-generator`

## Texture Upscaler

- **Input:** uploaded image + scale (2× / 4×)
- **Output:** upscaled PNG URL (Real-ESRGAN service or PIL mock)
- **API:** `POST /api/v1/texture-upscaler`
- Heavy work may run on the **Celery worker**

## Character Creator

- **Input:** character description (required; regenerate keeps last body)
- **Output:** image URL in object storage
- **API:** `POST /api/v1/character-creator`

## Sound Designer

- **Input:** prompt + kind (sfx / music / voice)
- **Output:** audio file URL (mock waveform or provider)
- **API:** `POST /api/v1/sound-designer`

## Playtester

- **Input:** design doc / feature description
- **Output:** QA-style report JSON (issues, severity, suggestions)
- **API:** `POST /api/v1/playtester`

## Localization

- **Input:** source strings / JSON + target languages
- **Output:** translated JSON or CSV
- **API:** `POST /api/v1/localization`

## Game Balancer

- **Input:** game data (classes, weapons, economy stats as JSON)
- **Output:** balance metrics, outliers, and tuning suggestions
- **API:** `POST /api/v1/game-balancer`

## Level Analyzer

- **Input:** level / path data for difficulty and reachability analysis
- **Output:** pathfinding summary, difficulty signals, choke points
- **API:** `POST /api/v1/level-analyzer`
- **Compare:** `POST /api/v1/level-analyzer/compare` — side-by-side analysis of two levels

## Store Description

- **Input:** game brief, platform (Steam / App Store / Google Play), tone, language
- **Output:** store listing copy (title, short/long description, tags, keywords)
- **API:** `POST /api/v1/store-description`
- UI language (`gf_lang`) influences default output language when the UI is Russian

## Playtest Analyzer

- **Input:** playtest session metrics / feedback notes
- **Output:** retention insights, friction points, prioritized recommendations
- **API:** `POST /api/v1/playtest-analyzer`

!!! note "Playtester vs Playtest Analyzer"
    **Playtester** reviews a design document before build. **Playtest Analyzer** interprets telemetry and feedback *after* sessions.

## Trailer Script

- **Input:** game pitch, trailer type (launch / teaser / gameplay), duration, tone
- **Output:** timed scenes, voiceover, text overlays, sound-design notes
- **API:** `POST /api/v1/trailer-script`

## Review Analyzer

- **Input:** player reviews (text, optional ratings / language)
- **Output:** sentiment, recurring issues, theme clusters, average rating signals
- **API:** `POST /api/v1/review-analyzer`

## Discord Bot (studio)

Configure a community bot (token encrypted at rest), commands, moderation helpers, and analytics. This is a multi-endpoint tool — not a single POST.

| Action | Method | Path |
|--------|--------|------|
| Save / update config | `POST` | `/api/v1/discord-bot/configure` |
| Status | `GET` | `/api/v1/discord-bot/status` |
| List commands | `GET` | `/api/v1/discord-bot/commands` |
| Create command | `POST` | `/api/v1/discord-bot/command` |
| Moderate message | `POST` | `/api/v1/discord-bot/moderate` |
| Simulate command | `POST` | `/api/v1/discord-bot/simulate-command` |
| Analyze community | `POST` | `/api/v1/discord-bot/analyze` |
| Analytics snapshot | `GET` | `/api/v1/discord-bot/analytics` |
| Tracked users | `GET` | `/api/v1/discord-bot/users` |

There is **no live Discord gateway worker** in the default deploy — moderation and commands are API/simulate MVP. Tokens are Fernet-encrypted before storage.

## Asset URLs

Generated files are stored in MinIO. In production, browsers open **signed** URLs under `https://<domain>/s3/...`. If a link fails, check [Deployment → VPS](../deployment/vps.md) (`S3_PUBLIC_ENDPOINT`).
