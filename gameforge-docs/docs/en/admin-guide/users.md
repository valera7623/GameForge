# Users and Roles

## Roles

| Role | Capabilities |
|------|----------------|
| `user` | Standard tools, own projects |
| `admin` | Platform administration (seed admin locally only) |

Studio **organization** roles are separate from global `UserRole`.

## Seed script

```bash
docker compose exec api python scripts/seed_db.py
```

Creates demo/admin users and sample project **only** when `APP_ENV` is not `production`. In production the script exits with an error.

!!! danger "Never seed production"
    Do not set `SEED_ON_DEPLOY=1` on a live VPS. Remove any leftover `demo@` / `admin@` accounts.

## Password reset

Requires working email (`resend` / `smtp`). Users open `/reset-password` with the emailed token.
