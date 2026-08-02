#!/usr/bin/env bash
# Runs on the VPS. Pull latest main and rebuild production stack.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BRANCH="${DEPLOY_BRANCH:-main}"
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)

echo "==> GameForge remote deploy ($(hostname)) branch=$BRANCH"

if [[ ! -f .env ]]; then
  echo "Missing .env in $ROOT — create it before deploying." >&2
  exit 1
fi

git fetch origin "$BRANCH"
git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"

docker network create traefik_network 2>/dev/null || true

echo "==> Build & up"
"${COMPOSE[@]}" pull postgres redis minio || true
"${COMPOSE[@]}" up -d --build --remove-orphans postgres redis minio minio-init api worker frontend traefik

echo "==> Wait for API (internal)"
ok=0
for i in $(seq 1 60); do
  if docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api \
      curl -sf http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; then
    echo "API is up"
    ok=1
    break
  fi
  sleep 2
done
if [[ "$ok" -ne 1 ]]; then
  echo "API health check timed out" >&2
  "${COMPOSE[@]}" logs api --tail 100 || true
  exit 1
fi

if [[ "${SEED_ON_DEPLOY:-0}" == "1" ]]; then
  echo "==> Seeding DB"
  "${COMPOSE[@]}" exec -T api python scripts/seed_db.py || true
fi

echo "==> Status"
"${COMPOSE[@]}" ps
DOMAIN_NAME="$(grep -E '^DOMAIN=' .env | cut -d= -f2- | tr -d '\r' || true)"
echo "Site: https://${DOMAIN_NAME:-localhost}"
echo "Done."
