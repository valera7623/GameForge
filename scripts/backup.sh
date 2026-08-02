#!/bin/sh
# Postgres + MinIO backup — loop every BACKUP_INTERVAL_SEC (default 24h)
# Retention: keep backups from the last 7 days on the volume; copy offsite separately.
set -eu

STAMP_FMT="%Y%m%dT%H%M%SZ"
OUT=/backups
INTERVAL="${BACKUP_INTERVAL_SEC:-86400}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"
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
  else
    echo "[backup] mc not found — skipping MinIO mirror"
  fi

  # Drop local artifacts older than KEEP_DAYS
  find "$OUT" -mindepth 1 -maxdepth 1 \( -name 'postgres_*.sql.gz' -o -type d -name 'minio_*' \) \
    -mtime +"$KEEP_DAYS" -exec rm -rf {} + 2>/dev/null || true

  echo "[backup] done $STAMP (retention ${KEEP_DAYS}d on volume; sync $OUT offsite regularly)"
}

if [ "${BACKUP_ONCE:-0}" = "1" ]; then
  run_once
  exit 0
fi

while true; do
  run_once || echo "[backup] failed, will retry after interval"
  sleep "$INTERVAL"
done
