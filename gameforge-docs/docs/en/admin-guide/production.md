# Production Checklist

Set these when `APP_ENV=production` (see also `.env.example`).

| Variable | Expected |
|----------|----------|
| `DEBUG` | `false` |
| `SECRET_KEY` | ≥32 chars, not a `change-me*` placeholder |
| `FRONTEND_URL` | `https://…` |
| `CORS_ORIGINS` | Explicit HTTPS origins (no `*`) |
| `COOKIE_SECURE` | `true` |
| `ALLOW_MOCK_BILLING` | `false` |
| `USE_MOCK_AI` | `true` to avoid AI spend, or `false` + `OPENAI_API_KEY` |
| `STABILITY_API_KEY` | Optional cloud Stable Image ([platform.stability.ai](https://platform.stability.ai)); set `IMAGE_PROVIDER=stability` for character art |
| `EMAIL_PROVIDER` | `resend` or `smtp` (not `console` unless `ALLOW_INSECURE_EMAIL=true`) |
| `DISABLE_BILLING` | `true` until payment keys exist |
| `S3_PUBLIC_ENDPOINT` | `https://<domain>/s3` |
| `S3_PUBLIC_URL` | `https://<domain>/s3/<bucket>` |
| `LOG_JSON` | `true` |
| `DOMAIN` / `ACME_EMAIL` | For Caddy certificates |

If `DISABLE_BILLING=false`, Stripe or YuKassa credentials are mandatory.

## DNS

- `@` → A record to VPS IP
- `www` → A to the same IP **or** CNAME to the apex hostname (never CNAME to a bare IP)
