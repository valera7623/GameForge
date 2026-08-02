# AI Game Dev Toolkit (GameForge)

Platform of **7 AI tools** for indie developers, studios, and modders: levels, quests, textures, characters, sound, playtesting, and localization.

## Quick start

```bash
cp .env.example .env
docker network create traefik_network || true
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

Or:

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec api python scripts/seed_db.py
```

| Service   | URL |
|-----------|-----|
| Frontend  | http://localhost:3000 |
| API       | http://localhost:8000 |
| Swagger   | http://localhost:8000/docs |
| MinIO     | http://localhost:9001 (`minioadmin` / `minioadmin`) |

**Demo accounts** (after seed):

- User: `demo@gamedev.ai` / `demo1234` (Indie plan)
- Admin: `admin@gamedev.ai` / `admin1234`

## Tools

| Tool | Endpoint | Output |
|------|----------|--------|
| Level Designer | `POST /api/v1/level-designer` | Tilemap JSON + Canvas preview |
| Quest Generator | `POST /api/v1/quest-generator` | Quest / dialogues JSON |
| Texture Upscaler | `POST /api/v1/texture-upscaler` | 2×/4× PNG |
| Character Creator | `POST /api/v1/character-creator` | Character image |
| Sound Designer | `POST /api/v1/sound-designer` | WAV/MP3 |
| Playtester | `POST /api/v1/playtester` | QA report JSON |
| Localization | `POST /api/v1/localization` | JSON/CSV translations |

## Example API flow

```bash
# Register
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"dev@studio.com","password":"pass123"}'

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"dev@studio.com","password":"pass123"}' | jq -r .access_token)

# Create project
PROJ=$(curl -s -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"Dungeon Explorer","engine":"unreal"}')
echo "$PROJ"
PID=$(echo "$PROJ" | jq -r .id)

# Generate level
curl -s -X POST http://localhost:8000/api/v1/level-designer \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{\"project_id\":\"$PID\",\"description\":\"Underwater temple with traps\"}" | jq .

# Generate character
curl -s -X POST http://localhost:8000/api/v1/character-creator \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"description":"Elf archer in leather armor"}' | jq .

# Export ZIP
curl -s -X GET "http://localhost:8000/api/v1/projects/$PID/export" \
  -H "Authorization: Bearer $TOKEN" -o game-assets.zip
```

## Architecture

```
Frontend (Vanilla JS + Vite + Nginx)
        ↓
API Gateway (FastAPI)
        ↓
AI Engine (GPT-4o / SD / Real-ESRGAN / ElevenLabs / MusicGen — mock fallbacks included)
        ↓
PostgreSQL · Redis · Celery · MinIO (S3)
```

With `USE_MOCK_AI=true` (default) the stack runs **without** paid API keys: procedural levels, synthetic audio, PIL upscale, placeholder characters, glossary localization.

### OpenAI via ProxyAPI

```env
USE_MOCK_AI=false
OPENAI_API_KEY=your_proxyapi_key
OPENAI_BASE_URL=https://api.proxyapi.ru/openai/v1
OPENAI_MODEL=gpt-4o
```

Key берётся из [ProxyAPI](https://proxyapi.ru). SDK тот же OpenAI — меняется только `base_url`.

### Email

```env
EMAIL_PROVIDER=console   # or smtp | resend
# SMTP_HOST=... SMTP_USER=... SMTP_PASSWORD=...
# RESEND_API_KEY=...
```

Password reset sends a link to `/src/pages/reset-password.html`. With `console`, the message is printed in API logs.

### Monthly leaderboard

`GET /api/v1/leaderboard?period=month` (default) ranks by `xp_this_month`.  
`?period=all` — lifetime XP.

### MusicGen / Real-ESRGAN

```env
REPLICATE_API_TOKEN=...          # MusicGen for kind=music
REALESRGAN_URL=http://realesrgan:8080
```

```bash
# Optional upscale microservice (PIL stub; swap for GPU Real-ESRGAN in prod)
docker compose --profile ai up -d realesrgan
# then set REALESRGAN_URL=http://realesrgan:8080 and restart api/worker
```

### Team seats (Studio)

Upgrade to Studio → auto-creates an organization. UI: **Team** page.  
API: `POST /api/v1/orgs`, invite, accept.

### On-prem (Enterprise)

```bash
docker compose -f docker-compose.yml -f docker-compose.onprem.yml up -d
```

Forces `FORCE_PLAN=enterprise`, disables billing checkout.

Set keys in `.env` and `USE_MOCK_AI=false` to call real providers.

## Plans

| Plan | Price | Generations / month |
|------|-------|---------------------|
| Free | $0 | 5 |
| Indie | $19 | 100 |
| Studio | $99 | 1000 |
| Enterprise | custom | unlimited / on-prem |

Billing: Stripe or YuKassa. Without keys, checkout **mock-upgrades** the plan instantly (dev mode).

## Dev frontend (hot reload)

```bash
docker compose --profile dev up frontend-dev
# → http://localhost:5173
```

## Traefik (HTTPS)

```bash
docker network create traefik_network || true
# set DOMAIN + ACME_EMAIL in .env
docker compose --profile traefik up -d
```

## Gamification

- +10 XP per generation
- Achievements at 1 / 10 / 50 / 100 / 500 generations
- Monthly leaderboard: `GET /api/v1/leaderboard`

## Project layout

See repository tree under `app/`, `frontend/`, `scripts/`.

## License

MIT — built as an MVP starter for AI Game Dev tooling.
