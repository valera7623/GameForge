# Troubleshooting

## Frontend container unhealthy

Healthcheck uses `pidof nginx` (not `wget`). Rebuild the frontend image if an old Compose file still probes wget.

## Asset URLs 403 / unreachable

- Confirm `S3_PUBLIC_ENDPOINT` and Caddy `/s3/` block
- Presign must target internal MinIO; public rewrite must keep SigV4 Host as `minio:9000` on the upstream

## API fails to start in production

Read the validate_settings error: weak `SECRET_KEY`, HTTP CORS, mock billing, missing mail provider, or billing enabled without keys.

## `/health/ready` returns 503

Postgres or Redis unreachable — check Compose health and network `gamedev`.

## Deploy race / container name conflicts

`deploy_remote.sh` uses a flock and rolling `up`. Wait for the lock; avoid parallel manual deploys during Actions.

## Email not sending

Production needs `EMAIL_PROVIDER=resend|smtp` and credentials. `console` only logs locally unless `ALLOW_INSECURE_EMAIL=true` (temporary).

## Mock vs real AI

`USE_MOCK_AI=true` avoids provider cost. Set `false` and provide `OPENAI_API_KEY` for live models; recreate api/worker after changing env.
