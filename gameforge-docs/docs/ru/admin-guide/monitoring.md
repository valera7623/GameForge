# Мониторинг

## Health

| Путь | Поведение |
|------|-----------|
| `GET /api/v1/health` | Liveness; в production урезанный ответ |
| `GET /api/v1/health/ready` | Postgres + Redis; **HTTP 503** при деградации |

Healthcheck Compose: ready API, live MinIO, `pidof nginx` у frontend.

## Логи

При `LOG_JSON=true` — JSON-строки с **`request_id`** (также заголовок `X-Request-ID`).

## Sentry (опционально)

Задайте `SENTRY_DSN`. API инициализирует FastAPI/Starlette; worker — Celery. Ошибки init на API не глотаются молча.

## Rate limit

Лимитер берёт первый hop из `X-Forwarded-For` (IP клиента за Caddy).
