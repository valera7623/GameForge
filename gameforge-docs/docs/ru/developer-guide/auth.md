# Авторизация

## Register / login

| Метод | Путь | Заметки |
|-------|------|---------|
| `POST` | `/auth/register` | Пользователь + Free-подписка |
| `POST` | `/auth/login` | Access token; cookies для браузера |
| `POST` | `/auth/refresh` | Ротация refresh |
| `POST` | `/auth/logout` | Очистка cookies |
| `POST` | `/auth/forgot-password` | Письмо со ссылкой |
| `POST` | `/auth/reset-password` | Применение токена |

## Cookies

| Cookie | Назначение |
|--------|------------|
| `gf_access` | Короткий access JWT |
| `gf_refresh` | Refresh token |

В production: `COOKIE_SECURE=true`. SameSite по умолчанию `lax`.

## API-ключи

- `POST /auth/api-keys`
- `DELETE /auth/api-keys/{id}`

## Лимиты auth

Для auth-маршрутов действует отдельный лимит (`AUTH_RATE_LIMIT_PER_MINUTE`).
