# Backup

Production Compose includes a **`backup`** profile service.

## What it does

- `pg_dump` of PostgreSQL → gzip on the `backup_data` volume
- MinIO mirror via `mc` (image includes both `pg_dump` and `mc`)
- Retention: **7 days** on-volume (`BACKUP_KEEP_DAYS`, default 7)
- Interval: `BACKUP_INTERVAL_SEC` (default 86400)

## Enable

Remote deploy already starts backup:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile backup up -d backup
```

One-shot:

```bash
BACKUP_ONCE=1 docker compose … run --rm backup
```

## Offsite

Copy `/backups` (or the named volume) to object storage / another host regularly. Volume retention alone is not disaster recovery.
