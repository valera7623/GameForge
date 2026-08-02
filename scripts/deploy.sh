#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> GameForge deploy (local)"

if [[ ! -f .env ]]; then
  echo "Creating .env from .env.example"
  cp .env.example .env
  # Generate secret if still default
  if grep -q "change-me-use-openssl-rand-hex-32" .env; then
    SECRET=$(openssl rand -hex 32)
    sed -i "s/change-me-use-openssl-rand-hex-32/$SECRET/" .env
    echo "Generated SECRET_KEY"
  fi
fi

echo "==> Building & starting stack"
docker compose pull postgres redis minio || true
docker compose up -d --build postgres redis minio minio-init api worker frontend

echo "==> Waiting for API health"
for i in $(seq 1 40); do
  if curl -sf http://localhost:8000/api/v1/health >/dev/null 2>&1; then
    echo "API is up"
    break
  fi
  sleep 2
  if [[ $i -eq 40 ]]; then
    echo "API health check timed out" >&2
    docker compose logs api --tail 80
    exit 1
  fi
done

echo "==> Seeding database (optional demo user — skipped when APP_ENV=production)"
docker compose exec -T api python scripts/seed_db.py || true

echo ""
echo "Ready:"
echo "  Frontend:  http://localhost:3000"
echo "  API:       http://localhost:8000"
echo "  API docs:  http://localhost:8000/docs"
echo "  MinIO:     http://localhost:9001"
echo ""
echo "Demo login (local seed only):  demo@gamedev.ai / demo123456"
echo ""
echo "HTTPS proxy:   docker compose --profile proxy up -d"
echo "Dev frontend:  docker compose --profile dev up frontend-dev"
