# Tool Endpoints

All routes are under `/api/v1` and require authentication unless noted.

| Tool | Method | Path |
|------|--------|------|
| Level Designer | `POST` | `/level-designer` |
| Quest Generator | `POST` | `/quest-generator` |
| Texture Upscaler | `POST` | `/texture-upscaler` |
| Character Creator | `POST` | `/character-creator` |
| Sound Designer | `POST` | `/sound-designer` |
| Playtester | `POST` | `/playtester` |
| Localization | `POST` | `/localization` |

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
```

Texture upscaler typically uses `multipart/form-data` for the file upload — prefer the UI or OpenAPI schema for exact fields.

## Quotas

Each successful generation consumes plan quota and awards XP. Exceeding the limit returns **402** (payment required / quota).

## Async jobs

Upscale, character, and sound may enqueue Celery tasks; poll status fields in the response or wait for the worker to finish before downloading assets.
