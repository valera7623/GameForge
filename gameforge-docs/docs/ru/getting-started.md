# Начало работы

Установка GameForge локально через Docker Compose, вход и первый запуск ИИ-инструмента.

## Требования

| Требование | Версия | Примечание |
|------------|--------|------------|
| Docker | 24+ | Compose v2 |
| Git | 2.x | Клонирование репозитория |
| curl / jq | любые | Опциональные smoke-тесты API |

## Клонирование и конфигурация

```bash
git clone https://github.com/valera7623/GameForge.git
cd gameforge
cp .env.example .env
```

Важные локальные значения:

| Переменная | Обычно локально | Назначение |
|------------|-----------------|------------|
| `APP_ENV` | `development` | Docs и мягкие проверки |
| `USE_MOCK_AI` | `true` | Без оплаты провайдеров |
| `SECRET_KEY` | генерируется скриптом | Подпись JWT / cookies |
| `DATABASE_URL` | Postgres в Compose | Async SQLAlchemy |
| `S3_ENDPOINT` | `http://minio:9000` | Object storage |
| `EMAIL_PROVIDER` | `console` | Письма в лог API |

!!! tip "Скрипт деплоя"
    `./scripts/deploy.sh` копирует `.env.example`, генерирует `SECRET_KEY` и поднимает стек.

## Запуск стека

```bash
docker compose up -d --build
docker compose exec api python scripts/seed_db.py
```

Проверка API:

```bash
curl -sf http://localhost:8000/api/v1/health
```

UI: [http://localhost:3000](http://localhost:3000).

## Первый вход

1. Войдите демо-аккаунтом **или** зарегистрируйтесь.
2. **Dashboard** → выберите инструмент (например Character Creator).
3. Отправьте промпт и дождитесь URL / JSON результата.

При `USE_MOCK_AI=true` используются mock-бэкенды — счёта OpenAI нет.

## Hot-reload фронтенда (опционально)

```bash
docker compose --profile dev up frontend-dev
# → http://localhost:5173
```

## Дальше

- [Руководство пользователя](user-guide/index.md)
- [Для разработчиков](developer-guide/index.md)
- Прод HTTPS: [Развёртывание → VPS](deployment/vps.md)
