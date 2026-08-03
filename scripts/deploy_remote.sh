#!/usr/bin/env bash
# Runs on the VPS. Pull latest main and rebuild production stack.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BRANCH="${DEPLOY_BRANCH:-main}"
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile backup)
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

# Re-exec so the rest of this script is the freshly pulled version (not a stale in-memory copy).
if [[ "${DEPLOY_REEXEC:-0}" != "1" ]]; then
  export DEPLOY_REEXEC=1
  exec "$0" "$@"
fi

DOMAIN_NAME="$(grep -E '^DOMAIN=' .env | cut -d= -f2- | tr -d '\r' || true)"
DOMAIN_NAME="${DOMAIN_NAME:-localhost}"

echo "==> Ensure infra + migrate"
"${COMPOSE[@]}" up -d --build --remove-orphans postgres redis minio minio-init
"${COMPOSE[@]}" build migrate
"${COMPOSE[@]}" run --rm migrate

echo "==> Build & up app stack"
# Rolling recreate without a full `down` (keeps volumes / network)
"${COMPOSE[@]}" up -d --build --remove-orphans \
  postgres redis minio minio-init api worker frontend docs caddy backup

# Sweep leftover conflict-renamed containers from interrupted recreates
docker ps -aq --filter name='gameforge' --filter status=exited 2>/dev/null \
  | xargs -r docker rm -f 2>/dev/null || true

echo "==> Wait for API readiness (internal)"
ok=0
for i in $(seq 1 60); do
  if "${COMPOSE[@]}" exec -T api curl -sf http://127.0.0.1:8000/api/v1/health/ready >/dev/null 2>&1; then
    echo "API is ready"
    ok=1
    break
  fi
  sleep 2
done
if [[ "$ok" -ne 1 ]]; then
  echo "API readiness timed out" >&2
  "${COMPOSE[@]}" logs api --tail 100 || true
  exit 1
fi

if [[ "${SEED_ON_DEPLOY:-0}" == "1" ]]; then
  echo "==> SEED_ON_DEPLOY=1 but seed is blocked in production — skipping"
fi

echo "==> Public smoke"
smoke_ok=0
for i in $(seq 1 30); do
  if curl -sf "https://${DOMAIN_NAME}/" >/dev/null 2>&1 \
    && curl -sf "https://${DOMAIN_NAME}/api/v1/health/ready" >/dev/null 2>&1; then
    echo "Public smoke OK (https://${DOMAIN_NAME})"
    smoke_ok=1
    break
  fi
  sleep 2
done
if [[ "$smoke_ok" -ne 1 ]]; then
  echo "Public smoke failed for https://${DOMAIN_NAME}" >&2
  "${COMPOSE[@]}" ps || true
  exit 1
fi

echo "==> Status"
"${COMPOSE[@]}" ps
echo "Site: https://${DOMAIN_NAME}"
echo "Done."
