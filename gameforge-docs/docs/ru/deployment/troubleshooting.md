# Устранение неполадок

## Frontend unhealthy

Healthcheck — `pidof nginx` (не `wget`). Пересоберите образ, если старый Compose ещё зовёт wget.

## Ассеты 403 / недоступны

- Проверьте `S3_PUBLIC_ENDPOINT` и блок Caddy `/s3/`
- Presign на внутренний MinIO; rewrite URL для браузера с корректным Host upstream

## API не стартует в production

Смотрите ошибку `validate_settings`: слабый `SECRET_KEY`, HTTP CORS, mock billing, почта, биллинг без ключей.

## `/health/ready` → 503

Недоступны Postgres или Redis — сеть `gamedev` и health сервисов.

## Гонка деплоев

`deploy_remote.sh` использует flock. Не запускайте параллельно с Actions вручную.

## Почта не уходит

Нужны `EMAIL_PROVIDER=resend|smtp` и ключи. `console` — только логи (или временный `ALLOW_INSECURE_EMAIL`).

## Mock vs реальный AI

`USE_MOCK_AI=true` экономит бюджет. Для живых моделей — `false` + `OPENAI_API_KEY`, затем recreate api/worker.
