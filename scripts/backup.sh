#!/bin/sh
# Postgres + MinIO backup — loop every BACKUP_INTERVAL_SEC (default 24h) for cron/sidecar use
set -eu

STAMP_FMT="%Y%m%dT%H%M%SZ"
OUT=/backups
INTERVAL="${BACKUP_INTERVAL_SEC:-86400}"
mkdir -p "$OUT"

run_once() {
  STAMP=$(date -u +"$STAMP_FMT")
  echo "[backup] starting $STAMP"
  PGPASSWORD="${POSTGRES_PASSWORD:-gamedev}" pg_dump \
    -h postgres -U "${POSTGRES_USER:-gamedev}" -d "${POSTGRES_DB:-gamedev}" \
    | gzip > "$OUT/postgres_$STAMP.sql.gz"

  if command -v mc >/dev/null 2>&1; then
    mc alias set local http://minio:9000 "${S3_ACCESS_KEY:-minioadmin}" "${S3_SECRET_KEY:-minioadmin}"
    mc mirror --overwrite "local/${S3_BUCKET:-gamedev-assets}" "$OUT/minio_$STAMP" || true
  fi

  ls -1t "$OUT"/postgres_*.sql.gz 2>/dev/null | tail -n +15 | xargs -r rm -f
  echo "[backup] done $STAMP"
}

if [ "${BACKUP_ONCE:-0}" = "1" ]; then
  run_once
  exit 0
fi

while true; do
  run_once || echo "[backup] failed, will retry after interval"
  sleep "$INTERVAL"
done
