# Обзор API

## Base URL

| Среда | Пример |
|-------|--------|
| Локальный API | `http://localhost:8000/api/v1` |
| Через frontend proxy | `http://localhost:3000/api/v1` |
| Production | `https://gameforge.website/api/v1` |

## Соглашения

- JSON тела запросов/ответов
- Auth: `Authorization: Bearer <access_token>` и/или HttpOnly cookies
- Rate limit → **429**
- Degraded ready → **503** на `/health/ready`
- Корреляция: `X-Request-ID`

## Пример потока

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"dev@studio.com","password":"pass123"}'

TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"dev@studio.com","password":"pass123"}' | jq -r .access_token)

PROJ=$(curl -s -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"Dungeon Explorer","engine":"unreal"}')
PID=$(echo "$PROJ" | jq -r .id)
```

Генерации — в [Эндпоинты инструментов](tools-api.md).
