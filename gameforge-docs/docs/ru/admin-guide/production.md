# Чеклист production

При `APP_ENV=production` (см. `.env.example`):

| Переменная | Ожидание |
|------------|----------|
| `DEBUG` | `false` |
| `SECRET_KEY` | ≥32 символов, не `change-me*` |
| `FRONTEND_URL` | `https://…` |
| `CORS_ORIGINS` | Явные HTTPS origins (без `*`) |
| `COOKIE_SECURE` | `true` |
| `ALLOW_MOCK_BILLING` | `false` |
| `USE_MOCK_AI` | `true` без трат на AI, или `false` + `OPENAI_API_KEY` |
| `STABILITY_API_KEY` | Опционально: облачный Stable Image ([platform.stability.ai](https://platform.stability.ai)); `IMAGE_PROVIDER=stability` чтобы использовать его для персонажей |
| `EMAIL_PROVIDER` | `resend` или `smtp` (не `console`, кроме `ALLOW_INSECURE_EMAIL=true`) |
| `DISABLE_BILLING` | `true`, пока нет платёжных ключей |
| `S3_PUBLIC_ENDPOINT` | `https://<domain>/s3` |
| `S3_PUBLIC_URL` | `https://<domain>/s3/<bucket>` |
| `LOG_JSON` | `true` |
| `DOMAIN` / `ACME_EMAIL` | Для сертификатов Caddy |

Если `DISABLE_BILLING=false`, нужны ключи Stripe или YuKassa.

## DNS

- `@` → A на IP VPS
- `www` → A на тот же IP **или** CNAME на apex (не CNAME на «голый» IP)
