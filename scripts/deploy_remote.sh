#!/usr/bin/env bash
# Runs on the VPS. Pull latest main and rebuild production stack.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BRANCH="${DEPLOY_BRANCH:-main}"
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)
LOCK_FILE="${HOME}/.gameforge-deploy.lock"

echo "==> GameForge remote deploy ($(hostname)) branch=$BRANCH"

if [[ ! -f .env ]]; then
  echo "Missing .env in $ROOT — create it before deploying." >&2
  exit 1
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "Another deploy is already running — waiting up to 20m…"
  flock -w 1200 9
fi

git fetch origin "$BRANCH"
git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"

docker network create traefik_network 2>/dev/null || true

echo "==> Clear stale compose containers (keep volumes)"
# Avoid "container name already in use" / half-recreated * _gameforge-* names
"${COMPOSE[@]}" down --remove-orphans --timeout 60 || true
# Sweep leftover conflict-renamed containers from interrupted recreates
docker ps -aq --filter name='gameforge' | xargs -r docker rm -f 2>/dev/null || true

echo "==> Build & up"
"${COMPOSE[@]}" pull postgres redis minio caddy || true
"${COMPOSE[@]}" up -d --build --remove-orphans \
  postgres redis minio minio-init api worker frontend caddy

echo "==> Wait for API (internal)"
ok=0
for i in $(seq 1 60); do
  if "${COMPOSE[@]}" exec -T api curl -sf http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; then
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
