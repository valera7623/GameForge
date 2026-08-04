# Docker (local)

## Full stack

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec api python scripts/seed_db.py
```

Services: `postgres`, `redis`, `minio`, `minio-init`, `api`, `worker`, `frontend`.

## Profiles

| Profile | Service | Purpose |
|---------|---------|---------|
| `dev` | `frontend-dev` | Vite HMR on :5173 |
| `ai` | `realesrgan` | CPU Real-ESRGAN (ncnn + llvmpipe); set `REALESRGAN_URL=http://realesrgan:8080` |
| `proxy` | `caddy` | Local HTTPS via Caddyfile |
| `migrate` | `migrate` | One-shot Alembic (always on in prod overlay) |
| `backup` | `backup` | Prod backups |

## Local HTTPS

```bash
# set DOMAIN + ACME_EMAIL in .env
docker compose --profile proxy up -d
```

## Helper script

```bash
./scripts/deploy.sh
```
