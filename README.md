<p align="center">
  <img src=".github/assets/logo.png" alt="GameForge" width="280">
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11+-blue" alt="Python"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.115+-green" alt="FastAPI"></a>
  <a href="https://docs.docker.com/compose/"><img src="https://img.shields.io/badge/docker-compose-24+-blue" alt="Docker"></a>
  <a href="https://github.com/valera7623/GameForge/actions/workflows/ci.yml"><img src="https://github.com/valera7623/GameForge/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
</p>

<p align="center">
  <strong>English</strong> ·
  <a href="README.ru.md">Русский</a>
</p>

<p align="center">
  <a href="https://docs.gameforge.website">Docs</a> ·
  <a href="https://gameforge.website">Production</a> ·
  <a href="https://github.com/valera7623/GameForge/issues">Issues</a>
</p>

---

## Table of contents

- [About](#about)
- [Live site](#live-site)
- [Features](#features)
- [Quick start](#quick-start)
- [Architecture](#architecture)
- [Plans & billing](#plans--billing)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [Team](#team)
- [License](#license)

---

## About

**GameForge** is an open-source **AI Game Dev Toolkit**: seven AI-powered tools for indie developers, studios, and modders — levels, quests, textures, characters, sound, playtesting, and localization — with projects, team seats, and ZIP export into Unity, Unreal, or Godot.

### The problem

Game teams burn time on repetitive content work:

- Level layouts, quest graphs, and localization tables are still hand-built
- Texture / character / audio pipelines are fragmented across tools
- Indie budgets cannot always afford live AI APIs during prototyping

### The solution

| Area | What GameForge provides |
|------|-------------------------|
| **Seven AI tools** | Level, quest, texture, character, sound, playtester, localization |
| **Projects & export** | Group assets per title and download a ZIP |
| **Mock or real AI** | `USE_MOCK_AI=true` for free local/prod prototyping; ProxyAPI / OpenAI when ready |
| **Team & plans** | Free / Indie / Studio / Enterprise (on-prem) |
| **Production stack** | Caddy HTTPS, MinIO `/s3/`, Celery workers, CI-gated deploy |

---

## Live site

**Production:** [https://gameforge.website](https://gameforge.website)

**Docs:** [https://docs.gameforge.website](https://docs.gameforge.website) · [RU](https://docs.gameforge.website/ru/)

Local demo accounts (after seed — **never** use in production):

| Role | Email | Password |
|------|-------|----------|
| User | `demo@gamedev.ai` | `demo123456` |
| Admin | `admin@gamedev.ai` | `admin123456` |

> Seed is refused when `APP_ENV=production`.

---

## Features

| Feature | Description |
|---------|-------------|
| **Level Designer** | Text → tilemap JSON + canvas preview |
| **Quest Generator** | Objectives, dialogues, branching JSON |
| **Texture Upscaler** | 2× / 4× PNG (Real-ESRGAN or PIL mock) |
| **Character Creator** | Concept art from a character brief |
| **Sound Designer** | SFX / music / voice (WAV/MP3) |
| **Playtester** | QA-style design report JSON |
| **Localization** | Multi-language JSON/CSV export |
| **Projects** | Per-engine projects + ZIP export |
| **Team seats** | Studio organizations, invites, roles |
| **Gamification** | XP, achievements, monthly leaderboard |
| **i18n UI** | English + Russian, light/dark theme |
| **Billing hooks** | Stripe / YuKassa (or `DISABLE_BILLING=true`) |

---

## Quick start

### Docker Compose (recommended)

```bash
git clone https://github.com/valera7623/GameForge.git
cd GameForge

cp .env.example .env
docker compose up -d --build
docker compose exec api python scripts/seed_db.py

# Health checks
curl -s http://localhost:8000/api/v1/health
curl -s http://localhost:8000/api/v1/health/ready
```

Or: `./scripts/deploy.sh`

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger (non-production) | http://localhost:8000/docs |
| MinIO console | http://localhost:9001 |

### Hot-reload frontend

```bash
docker compose --profile dev up frontend-dev
# → http://localhost:5173
```

### Real AI providers

```env
USE_MOCK_AI=false
OPENAI_API_KEY=your_proxyapi_key
OPENAI_BASE_URL=https://api.proxyapi.ru/openai/v1
OPENAI_MODEL=gpt-4o
```

Key from [ProxyAPI](https://proxyapi.ru) — same OpenAI SDK, different `base_url`.

Optional: `STABILITY_API_KEY` + `IMAGE_PROVIDER=stability` (cloud Stable Image, no local SD), `REALESRGAN_URL`, `REPLICATE_API_TOKEN` (MusicGen), `ELEVENLABS_API_KEY`.

```bash
docker compose --profile ai up -d realesrgan
```

### Production (VPS + Caddy)

```bash
# DNS: @, www, docs → A <VPS_IP>
# Fill .env from the Production checklist in .env.example

docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile backup up -d --build
# or on the server: ./scripts/deploy_remote.sh
```

| Variable | Notes |
|----------|--------|
| `APP_ENV=production` | Fail-closed settings validation |
| `USE_MOCK_AI` | `true` to avoid AI spend; `false` + `OPENAI_API_KEY` for live models |
| `DISABLE_BILLING` | `true` until Stripe/YuKassa keys exist |
| `EMAIL_PROVIDER` | `resend` or `smtp` |
| `S3_PUBLIC_ENDPOINT` | `https://<domain>/s3` |

Deploy: GitHub Actions **Deploy** after green **CI** on `main`. Details: [docs → VPS](https://docs.gameforge.website/deployment/vps/).

### On-prem (Enterprise)

```bash
docker compose -f docker-compose.yml -f docker-compose.onprem.yml up -d
```

Forces `FORCE_PLAN=enterprise`, disables billing checkout.

### Example API flow

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@gamedev.ai","password":"demo123456"}' | jq -r .access_token)

curl -s -X POST http://localhost:8000/api/v1/character-creator \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"description":"Elf archer in leather armor"}' | jq .
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GameForge (v1.2.0)                        │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Vite MPA + Nginx)  │  FastAPI /api/v1  │  Celery │
├───────────────────────────────┴───────────────────┴─────────┤
│  AI tools (mock or OpenAI / Real-ESRGAN / MusicGen / …)     │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL  │  Redis (rate limit, broker)  │  MinIO (S3)   │
└─────────────────────────────────────────────────────────────┘
         ▲ Caddy + Let's Encrypt (production) · public /s3/
```

**Stack:** FastAPI · SQLAlchemy · Alembic · PostgreSQL 15 · Redis 7 · Celery · MinIO · Vite · Nginx · Caddy

---

## Plans & billing

| Plan | Price | Generations / month |
|------|-------|---------------------|
| Free | $0 | 5 |
| Indie | $19 | 100 |
| Studio | $99 | 1000 |
| Enterprise | custom | unlimited / on-prem |

Billing: Stripe or YuKassa. In production without keys, set `DISABLE_BILLING=true`. Locally, mock upgrades work when `ALLOW_MOCK_BILLING=true`.

---

## Documentation

| Section | Description |
|---------|-------------|
| [User Guide](https://docs.gameforge.website/user-guide/) | Dashboard, tools, team, billing |
| [Admin Guide](https://docs.gameforge.website/admin-guide/) | Production checklist, monitoring, backups |
| [Developer Guide](https://docs.gameforge.website/developer-guide/) | API, auth, tool endpoints |
| [Architecture](https://docs.gameforge.website/architecture/) | Components and data flows |
| [Deployment](https://docs.gameforge.website/deployment/) | Docker, VPS, troubleshooting |

Local docs (MkDocs Material, EN/RU):

```bash
cd gameforge-docs && ./mkdocs.sh serve
# → http://127.0.0.1:8001
```

---

## Contributing

Issues, PRs, and feedback are welcome.

1. Fork → `git checkout -b feature/my-feature`
2. Code + tests + docs
3. `ruff check app tests` and `pytest -q`
4. Open a Pull Request

---

## Team

| Name | Role | Contact |
|------|------|---------|
| **Valeriy Popov** | Founder & Lead Developer | [GitHub](https://github.com/valera7623) · [valera7623@gmail.com](mailto:valera7623@gmail.com) |

---

## License

[MIT License](LICENSE) © 2026 Valeriy Popov

---

## Support

- Star the repo on [GitHub](https://github.com/valera7623/GameForge)
- [Report a bug](https://github.com/valera7623/GameForge/issues)
- Docs: [https://docs.gameforge.website](https://docs.gameforge.website)

---

<p align="center">
  <strong>GameForge v1.2.0</strong> — seven AI tools for game developers<br>
  Built for indies, studios, and modders who ship faster
</p>
