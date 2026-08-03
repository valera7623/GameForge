# VPS (production)

Референс: **https://gameforge.website** на Linux VPS с Docker.

## DNS

1. Apex `@` → **A** `VPS_IP`
2. `www` → **A** тот же IP или **CNAME** → `gameforge.website` (не на «голый» IP)

## Стек

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile backup up -d --build
```

Или на сервере:

```bash
./scripts/deploy_remote.sh
```

Скрипт: flock → pull `main` → infra + **migrate** → rolling up → smoke `/` и `/api/v1/health/ready`.

## Caddy

- Авто HTTPS (Let’s Encrypt)
- Редиректы HTTP и `www` на HTTPS apex
- Прокси `/s3/*` → MinIO с сохранением Host для SigV4

## Публичные ассеты

```env
S3_ENDPOINT=http://minio:9000
S3_PUBLIC_ENDPOINT=https://gameforge.website/s3
S3_PUBLIC_URL=https://gameforge.website/s3/gamedev-assets
```

## CI deploy

Workflow **Deploy** только после успешного **CI** на `main` (`workflow_run`) или вручную. In-progress деплои не отменяются.

## Чеклист

[Админ → Чеклист production](../admin-guide/production.md).
