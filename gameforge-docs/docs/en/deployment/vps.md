# VPS Production

Reference deployment: **https://gameforge.website** on a Linux VPS with Docker.

## DNS

1. Apex `@` → **A** `VPS_IP`
2. `www` → **A** `VPS_IP` or **CNAME** → `gameforge.website` (not to a raw IP)

## Stack

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile backup up -d --build
```

Or on the server after git pull:

```bash
./scripts/deploy_remote.sh
```

The remote script:

1. Takes a flock
2. Pulls `main`
3. Starts infra + **migrate**
4. Rolling `up` of api/worker/frontend/caddy/backup
5. Smokes `https://$DOMAIN/` and `/api/v1/health/ready`

## Caddy

- Automatic HTTPS (Let’s Encrypt)
- Redirects HTTP and `www` to HTTPS apex
- Proxies `/s3/*` → MinIO with Host preserved for SigV4

## Public assets

```env
S3_ENDPOINT=http://minio:9000
S3_PUBLIC_ENDPOINT=https://gameforge.website/s3
S3_PUBLIC_URL=https://gameforge.website/s3/gamedev-assets
```

Presign uses the internal endpoint; URLs are rewritten for the browser.

## CI deploy

GitHub Actions workflow **Deploy** runs only after a successful **CI** on `main` (`workflow_run`), or via `workflow_dispatch`. Concurrency does not cancel in-progress deploys.

## Checklist

See [Admin → Production Checklist](../admin-guide/production.md).
