# Users and Roles

## Platform roles

| Role | Capabilities |
|------|----------------|
| `user` | Standard tools, own projects |
| `enterprise` | Legacy enterprise platform role (plan usually on subscription) |
| `support` | Admin panel: read users, generations, dashboard |
| `manager` | Admin panel: read + content CMS write |
| `admin` | Manage users (block/edit/role except `super_admin`), tools, subscriptions |
| `super_admin` | Full admin panel including platform settings and AI pricing |

Studio **organization** roles (`owner` / `admin` / `member`) are separate from global `UserRole`.

## Admin panel

Staff sign in at **`/admin/login`** (or open **`/admin`** after logging in with a staff account).

API prefix: `/api/v1/admin/*` (cookie session, same as the app).

| Area | Path |
|------|------|
| Dashboard | `/admin` |
| Users | `/admin/users`, `/admin/user?id=` |
| Generations | `/admin/generations` |
| Subscriptions | `/admin/subscriptions` |
| Tools on/off | `/admin/tools` |
| AI models / costs | `/admin/ai-models` |
| Content CMS | `/admin/content` |
| Ops logs | `/admin/logs` |
| Settings | `/admin/settings` (super_admin write) |

Disabled tools return **503** on generation endpoints.

## Seed script

```bash
docker compose exec api python scripts/seed_db.py
```

Creates demo/admin users and sample project **only** when `APP_ENV` is not `production`. In production the script exits with an error.

Local seed admin: `admin@gamedev.ai` / `admin123456` with role **`super_admin`**.

!!! danger "Never seed production"
    Do not set `SEED_ON_DEPLOY=1` on a live VPS. Remove any leftover `demo@` / `admin@` accounts.

## Password reset

Requires working email (`resend` / `smtp`). Users open `/reset-password` with the emailed token.
