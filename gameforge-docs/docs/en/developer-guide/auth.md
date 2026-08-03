# Authentication

## Register / login

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `/auth/register` | Creates user + free subscription |
| `POST` | `/auth/login` | Returns access token; sets cookies when browser client |
| `POST` | `/auth/refresh` | Refresh token rotation |
| `POST` | `/auth/logout` | Clears session cookies |
| `POST` | `/auth/forgot-password` | Emails reset link |
| `POST` | `/auth/reset-password` | Consumes token |

## Cookies

| Cookie | Purpose |
|--------|---------|
| `gf_access` | Short-lived access JWT |
| `gf_refresh` | Refresh token |

`COOKIE_SECURE=true` in production. SameSite defaults to `lax`.

## API keys

Authenticated users can create personal API keys:

- `POST /auth/api-keys`
- `DELETE /auth/api-keys/{id}`

Use the key in API requests as documented by the auth module (Bearer / header scheme supported by the backend).

## Auth rate limits

Stricter limits apply to auth routes (`AUTH_RATE_LIMIT_PER_MINUTE`) to reduce brute-force risk.
