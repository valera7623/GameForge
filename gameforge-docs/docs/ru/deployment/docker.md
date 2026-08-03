# Docker (локально)

## Полный стек

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec api python scripts/seed_db.py
```

Сервисы: `postgres`, `redis`, `minio`, `minio-init`, `api`, `worker`, `frontend`.

## Профили

| Профиль | Сервис | Назначение |
|---------|--------|------------|
| `dev` | `frontend-dev` | Vite HMR :5173 |
| `ai` | `realesrgan` | Опциональный upscale |
| `proxy` | `caddy` | Локальный HTTPS |
| `migrate` | `migrate` | One-shot Alembic |
| `backup` | `backup` | Бэкапы (prod) |

## Локальный HTTPS

```bash
docker compose --profile proxy up -d
```

## Скрипт

```bash
./scripts/deploy.sh
```
