# API Overview

## Base URL

| Environment | Example |
|-------------|---------|
| Local API | `http://localhost:8000/api/v1` |
| Local via frontend proxy | `http://localhost:3000/api/v1` |
| Production | `https://gameforge.website/api/v1` |

## Conventions

- JSON request/response bodies
- Auth via `Authorization: Bearer <access_token>` and/or HttpOnly cookies
- Rate limits return **429**
- Readiness failures return **503** on `/health/ready`
- Correlation: send or receive `X-Request-ID`

## Example flow

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
PID=$(echo "$PROJ" | jq -r .id)
```

See [Tool Endpoints](tools-api.md) for generation calls.
