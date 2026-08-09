# Биллинг и тарифы

Оплата ориентирована на Россию: **ЮKassa**, валюта **RUB**. Суммы в API (`price_cents`) — в копейках.

| План | Цена | Генераций / месяц |
|------|------|-------------------|
| Free | 0 ₽ | 5 |
| Indie | 1 990 ₽/мес | 100 |
| Studio | 9 990 ₽/мес | 1000 |
| Enterprise | custom | unlimited / on-prem |

## Пакеты LocForge (разовые)

| Пакет | Слова | Цена |
|-------|-------|------|
| Starter | 5 000 | 4 990 ₽ |
| Indie | 25 000 | 14 990 ₽ |
| Studio | 100 000 | 39 990 ₽ |

## Биллинг выключен

При `DISABLE_BILLING=true`:

- Checkout не списывает деньги
- Mock-апгрейды в production **запрещены** (`ALLOW_MOCK_BILLING=false`)

## Провайдер

| Переменная | Значение |
|------------|----------|
| `BILLING_PROVIDER` | `yukassa` (по умолчанию) |
| `BILLING_CURRENCY` | `RUB` |
| `YUKASSA_SHOP_ID` / `YUKASSA_SECRET_KEY` | ключи магазина |
| `YUKASSA_VAT_CODE` | код НДС для чека 54-ФЗ (`1` = без НДС; `0` = не слать receipt) |

Webhook: `POST /api/v1/billing/webhook/yukassa`.

Stripe остаётся опциональным fallback (`BILLING_PROVIDER=stripe`).

## Локальный mock

В development при `ALLOW_MOCK_BILLING=true` план/пакет можно применить без реальной оплаты. В production не включать.
