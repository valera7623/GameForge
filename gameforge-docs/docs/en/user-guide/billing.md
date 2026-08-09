# Billing and Plans

Primary market: **Russia**. Default provider **YuKassa**, currency **RUB**. API `price_cents` values are kopecks.

| Plan | Price | Generations / month |
|------|-------|---------------------|
| Free | 0 ₽ | 5 |
| Indie | 1 990 ₽/mo | 100 |
| Studio | 9 990 ₽/mo | 1000 |
| Enterprise | custom | unlimited / on-prem |

## LocForge word packs (one-time)

| Pack | Words | Price |
|------|-------|-------|
| Starter | 5,000 | 4 990 ₽ |
| Indie | 25,000 | 14 990 ₽ |
| Studio | 100,000 | 39 990 ₽ |

## Disabled billing

When `DISABLE_BILLING=true`:

- Checkout does not charge
- Mock upgrades are **blocked** in production (`ALLOW_MOCK_BILLING` must be false)

## Provider

| Variable | Value |
|----------|-------|
| `BILLING_PROVIDER` | `yukassa` (default) |
| `BILLING_CURRENCY` | `RUB` |
| `YUKASSA_SHOP_ID` / `YUKASSA_SECRET_KEY` | shop credentials |
| `YUKASSA_VAT_CODE` | 54-FZ receipt VAT (`1` = no VAT; `0` = omit receipt) |

Webhook: `POST /api/v1/billing/webhook/yukassa`.

Stripe remains an optional fallback (`BILLING_PROVIDER=stripe`).

## Local mock

In development with `ALLOW_MOCK_BILLING=true`, checkout can apply a plan/pack instantly. Never enable in production.
