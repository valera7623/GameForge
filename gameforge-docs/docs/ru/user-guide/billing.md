# Биллинг и тарифы

| План | Цена (USD) | Генераций / месяц |
|------|------------|-------------------|
| Free | $0 | 5 |
| Indie | $19 | 100 |
| Studio | $99 | 1000 |
| Enterprise | custom | unlimited / on-prem |

## Биллинг выключен (типичный прод)

При `DISABLE_BILLING=true` (пока нет ключей Stripe/YuKassa):

- Checkout не списывает карты
- Mock-апгрейды в production **запрещены** (`ALLOW_MOCK_BILLING=false`)
- Доступны Free-квоты и принудительные on-prem планы

## Провайдеры

| Провайдер | Переменные |
|-----------|------------|
| Stripe | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, price IDs |
| YuKassa | `YUKASSA_SHOP_ID`, `YUKASSA_SECRET_KEY` |

`BILLING_PROVIDER` должен соответствовать. В проде при включённом биллинге ключи обязательны.

## Локальный mock

В development при `ALLOW_MOCK_BILLING=true` план можно применить мгновенно для тестов. В production не включать.
