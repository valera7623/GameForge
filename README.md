# AI Game Dev Toolkit (GameForge)

Platform of **7 AI tools** for indie developers, studios, and modders: levels, quests, textures, characters, sound, playtesting, and localization.

## Local quick start

```bash
cp .env.example .env
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
| Swagger   | http://localhost:8000/docs (disabled when `APP_ENV=production`) |
| MinIO     | http://localhost:9001 (`minioadmin` / `minioadmin`) |

**Local demo accounts** (after seed; never use these in production):

- User: `demo@gamedev.ai` / `demo123456` (Indie plan)
- Admin: `admin@gamedev.ai` / `admin123456`

Seed is refused when `APP_ENV=production`.

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

With `USE_MOCK_AI=true` (default locally) the stack runs **without** paid API keys: procedural levels, synthetic audio, PIL upscale, placeholder characters, glossary localization.

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

Password reset sends a link to `/reset-password`. With `console`, the message is printed in API logs. Production forbids `console` unless `ALLOW_INSECURE_EMAIL=true` (temporary).

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

Billing: Stripe or YuKassa. Without keys, set `DISABLE_BILLING=true` (required in production until a provider is configured). Locally, mock upgrades work when `ALLOW_MOCK_BILLING=true`.

## Dev frontend (hot reload)

```bash
docker compose --profile dev up frontend-dev
# → http://localhost:5173
```

## Production (Caddy + VPS)

HTTPS is served by **Caddy** (Let’s Encrypt). Assets are signed against a public MinIO path proxied at `/s3/`.

```bash
# DNS (Timeweb / any DNS host)
#   @   → A     <VPS_IP>
#   www → A     <VPS_IP>   # or CNAME → apex hostname (never CNAME to a bare IP)

# On the VPS, fill .env using the Production checklist in .env.example, then:
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile backup up -d --build
```

Local proxy profile (same Caddyfile):

```bash
# set DOMAIN + ACME_EMAIL in .env
docker compose --profile proxy up -d
```

**Production `.env` essentials**

| Variable | Value |
|----------|--------|
| `APP_ENV` | `production` |
| `USE_MOCK_AI` | `true` to avoid paid AI spend; `false` + `OPENAI_API_KEY` for real providers |
| `DISABLE_BILLING` | `true` until Stripe/YuKassa keys exist |
| `EMAIL_PROVIDER` | `resend` or `smtp` (not `console`) |
| `S3_PUBLIC_ENDPOINT` | `https://<domain>/s3` |
| `S3_PUBLIC_URL` | `https://<domain>/s3/gamedev-assets` |
| `COOKIE_SECURE` / `LOG_JSON` | `true` |

Deploy: GitHub Actions `Deploy` runs only after a green `CI` on `main` (or `workflow_dispatch`). Remote script: `scripts/deploy_remote.sh` (migrate → rolling up → public smoke on `/` and `/api/v1/health/ready`).

Backups: compose profile `backup` (Postgres dump + MinIO mirror, 7-day volume retention). Copy `/backups` offsite regularly.

## Gamification

- +10 XP per generation
- Achievements at 1 / 10 / 50 / 100 / 500 generations
- Monthly leaderboard: `GET /api/v1/leaderboard`

## Project layout

See repository tree under `app/`, `frontend/`, `scripts/`.

## License

MIT — built as an MVP starter for AI Game Dev tooling.
