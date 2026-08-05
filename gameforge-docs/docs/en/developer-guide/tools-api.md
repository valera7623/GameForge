# Tool Endpoints

All routes are under `/api/v1` and require authentication unless noted.

## Single-shot tools

| Tool | Method | Path |
|------|--------|------|
| Level Designer | `POST` | `/level-designer` |
| Quest Generator | `POST` | `/quest-generator` |
| Texture Upscaler | `POST` | `/texture-upscaler` |
| Character Creator | `POST` | `/character-creator` |
| Sound Designer | `POST` | `/sound-designer` |
| Playtester | `POST` | `/playtester` |
| Localization | `POST` | `/localization` |
| Game Balancer | `POST` | `/game-balancer` |
| Level Analyzer | `POST` | `/level-analyzer` |
| Level Analyzer (compare) | `POST` | `/level-analyzer/compare` |
| Store Description | `POST` | `/store-description` |
| Playtest Analyzer | `POST` | `/playtest-analyzer` |
| Trailer Script | `POST` | `/trailer-script` |
| Review Analyzer | `POST` | `/review-analyzer` |

Successful runs create a **generation** row (`ToolType` enum) with `output_data` / asset URLs. Exact request bodies are in OpenAPI (`/docs` when not production) and the UI forms.

## Discord Bot

| Action | Method | Path |
|--------|--------|------|
| Configure | `POST` | `/discord-bot/configure` |
| Status | `GET` | `/discord-bot/status` |
| List commands | `GET` | `/discord-bot/commands` |
| Create command | `POST` | `/discord-bot/command` |
| Moderate | `POST` | `/discord-bot/moderate` |
| Simulate command | `POST` | `/discord-bot/simulate-command` |
| Analyze | `POST` | `/discord-bot/analyze` |
| Analytics | `GET` | `/discord-bot/analytics` |
| Users | `GET` | `/discord-bot/users` |

`analyze` consumes generation quota like other tools; configure / moderate / simulate are control-plane helpers.

## Examples

```bash
# Level
curl -s -X POST http://localhost:8000/api/v1/level-designer \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{\"project_id\":\"$PID\",\"description\":\"Underwater temple with traps\"}" | jq .

# Character
curl -s -X POST http://localhost:8000/api/v1/character-creator \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"description":"Elf archer in leather armor"}' | jq .

# Store description
curl -s -X POST http://localhost:8000/api/v1/store-description \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"game_name":"Dungeon Explorer","platform":"steam","genre":"Action RPG","description":"Roguelike dungeons"}' | jq .

# Level compare
curl -s -X POST http://localhost:8000/api/v1/level-analyzer/compare \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"level_a":{...},"level_b":{...}}' | jq .
```

Texture upscaler typically uses `multipart/form-data` for the file upload — prefer the UI or OpenAPI schema for exact fields.

## Quotas

Each successful generation consumes plan quota and awards XP. Exceeding the limit returns **402** (payment required / quota).

## Rate limits

Auth and tool routes use Redis-backed sliding windows (in-memory fallback). In `APP_ENV=test`, rate limiting is **disabled** so CI can run the full suite.

## Async jobs

Upscale, character, and sound may enqueue Celery tasks; poll status fields in the response or wait for the worker to finish before downloading assets.
