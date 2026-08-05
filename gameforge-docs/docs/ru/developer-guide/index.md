# Для разработчиков

Интеграция с GameForge по HTTP. Базовый путь: **`/api/v1`**.

## Содержание

| Страница | Темы |
|----------|------|
| [Обзор API](api-overview.md) | Base URL, ошибки |
| [Авторизация](auth.md) | Register, login, cookies, API keys |
| [Эндпоинты инструментов](tools-api.md) | Все четырнадцать tools, Discord, примеры |

## OpenAPI локально

Если `APP_ENV` не `production`:

- http://localhost:8000/docs
- http://localhost:8000/redoc

В production эти маршруты отключены.

## Запуск тестов

```bash
export APP_ENV=test USE_MOCK_AI=true ALLOW_MOCK_BILLING=true FORCE_PLAN=studio
export DATABASE_URL=postgresql+asyncpg://gamedev:gamedev@localhost:5432/gamedev_test
export REDIS_URL=redis://localhost:6379/15
ruff check app tests
pytest -q
```

При `APP_ENV=test` HTTP rate limiting выключен, а middleware API-логов не пишет в глобальный DB engine (избегает проблем event loop в pytest-asyncio).
