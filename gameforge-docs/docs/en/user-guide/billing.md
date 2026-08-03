# Billing and Plans

| Plan | Price (USD) | Generations / month |
|------|-------------|---------------------|
| Free | $0 | 5 |
| Indie | $19 | 100 |
| Studio | $99 | 1000 |
| Enterprise | custom | unlimited / on-prem |

## Disabled billing (current production default)

When `DISABLE_BILLING=true` (recommended until Stripe or YuKassa keys exist):

- Checkout / portal endpoints do not charge cards
- Plan upgrades via mock payment are **blocked** in production (`ALLOW_MOCK_BILLING` must be false)
- You can still use Free quotas and admin/on-prem forced plans

## Providers

| Provider | Env vars |
|----------|----------|
| Stripe | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, price IDs |
| YuKassa | `YUKASSA_SHOP_ID`, `YUKASSA_SECRET_KEY` |

Set `BILLING_PROVIDER` accordingly. Production validation requires real keys if billing is enabled.

## Local mock upgrades

In development, with `ALLOW_MOCK_BILLING=true`, checkout can instantly apply a plan for testing. Never enable this in production.
