# Developer Guide

Integrate with GameForge over HTTP. Base path: **`/api/v1`**.

## Contents

| Page | Topics |
|------|--------|
| [API Overview](api-overview.md) | Base URL, versioning, errors |
| [Auth](auth.md) | Register, login, cookies, API keys |
| [Tool Endpoints](tools-api.md) | All fourteen tools, Discord routes, sample calls |

## Local OpenAPI

When `APP_ENV` is not `production`, interactive docs are at:

- http://localhost:8000/docs
- http://localhost:8000/redoc

In production those routes are disabled.

## Running tests

```bash
export APP_ENV=test USE_MOCK_AI=true ALLOW_MOCK_BILLING=true FORCE_PLAN=studio
export DATABASE_URL=postgresql+asyncpg://gamedev:gamedev@localhost:5432/gamedev_test
export REDIS_URL=redis://localhost:6379/15
ruff check app tests
pytest -q
```

In `APP_ENV=test`, HTTP rate limiting is skipped and API request-log middleware does not write to the global DB engine (avoids event-loop issues under pytest-asyncio).
