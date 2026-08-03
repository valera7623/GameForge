# Monitoring

## Health endpoints

| Path | Behaviour |
|------|-----------|
| `GET /api/v1/health` | Liveness; minimal fields in production |
| `GET /api/v1/health/ready` | Checks Postgres + Redis; **HTTP 503** if degraded |

Compose healthchecks probe the API ready URL, MinIO live endpoint, and `pidof nginx` on the frontend.

## Logs

With `LOG_JSON=true` (production default in Compose), logs are JSON lines including **`request_id`** (also returned as `X-Request-ID`).

## Sentry (optional)

Set `SENTRY_DSN`. The API initializes Sentry with FastAPI / Starlette integrations; Celery workers initialize Celery integration. Init failures are not swallowed silently on the API path.

## Rate limiting

Redis-backed limiter uses the first `X-Forwarded-For` hop (client IP behind Caddy), not the proxy address.
