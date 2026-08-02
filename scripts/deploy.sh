#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> GameForge deploy"

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

docker network create traefik_network 2>/dev/null || true

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

echo "==> Seeding database (optional demo user)"
docker compose exec -T api python scripts/seed_db.py || true

echo ""
echo "Ready:"
echo "  Frontend:  http://localhost:3000"
echo "  API:       http://localhost:8000"
echo "  API docs:  http://localhost:8000/docs"
echo "  MinIO:     http://localhost:9001"
echo ""
echo "Demo login:  demo@gamedev.ai / demo1234"
echo ""
echo "With Traefik:  docker compose --profile traefik up -d"
echo "Dev frontend:  docker compose --profile dev up frontend-dev"
