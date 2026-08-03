# Getting Started

Install GameForge locally with Docker Compose, create an account (or use seed demos), and run your first AI tool.

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Docker | 24+ | Compose v2 plugin |
| Git | 2.x | Clone the repository |
| curl / jq | any | Optional API smoke tests |

## Clone and configure

```bash
git clone https://github.com/valera7623/GameForge.git
cd gameforge
cp .env.example .env
```

Important local defaults:

| Variable | Typical local value | Purpose |
|----------|---------------------|---------|
| `APP_ENV` | `development` | Enables docs, looser gates |
| `USE_MOCK_AI` | `true` | No paid provider spend |
| `SECRET_KEY` | change via deploy script | JWT / cookie signing |
| `DATABASE_URL` | Postgres in Compose | Async SQLAlchemy |
| `S3_ENDPOINT` | `http://minio:9000` | Object storage |
| `EMAIL_PROVIDER` | `console` | Prints mail to API logs |

!!! tip "Deploy helper"
    `./scripts/deploy.sh` copies `.env.example`, generates a `SECRET_KEY`, and starts the stack.

## Start the stack

```bash
docker compose up -d --build
docker compose exec api python scripts/seed_db.py
```

Wait until the API answers:

```bash
curl -sf http://localhost:8000/api/v1/health
```

Open the UI at [http://localhost:3000](http://localhost:3000).

## First login

1. Sign in with a seed account **or** register a new email.
2. Open **Dashboard** → pick a tool (for example Character Creator).
3. Submit a short prompt and wait for the result URL / JSON.

With `USE_MOCK_AI=true`, generations use procedural / placeholder backends — no OpenAI bill.

## Hot-reload frontend (optional)

```bash
docker compose --profile dev up frontend-dev
# → http://localhost:5173
```

## Next steps

- Read the [User Guide](user-guide/index.md) for each tool.
- Call the API from scripts — see [Developer Guide](developer-guide/index.md).
- For HTTPS on a VPS, follow [Deployment → VPS](deployment/vps.md).
