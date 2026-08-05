# Эндпоинты инструментов

Все маршруты под `/api/v1`, нужна аутентификация (если не указано иное).

## Одноразовые tools

| Инструмент | Метод | Путь |
|------------|-------|------|
| Level Designer | `POST` | `/level-designer` |
| Quest Generator | `POST` | `/quest-generator` |
| Texture Upscaler | `POST` | `/texture-upscaler` |
| Character Creator | `POST` | `/character-creator` |
| Sound Designer | `POST` | `/sound-designer` |
| Playtester | `POST` | `/playtester` |
| Localization | `POST` | `/localization` |
| Game Balancer | `POST` | `/game-balancer` |
| Level Analyzer | `POST` | `/level-analyzer` |
| Level Analyzer (compare) | `POST` | `/level-analyzer/compare` |
| Store Description | `POST` | `/store-description` |
| Playtest Analyzer | `POST` | `/playtest-analyzer` |
| Trailer Script | `POST` | `/trailer-script` |
| Review Analyzer | `POST` | `/review-analyzer` |

Успешный запуск создаёт запись **generation** (`ToolType`) с `output_data` / URL ассетов. Точные тела запросов — в OpenAPI (`/docs` вне production) и формах UI.

## Discord Bot

| Действие | Метод | Путь |
|----------|-------|------|
| Configure | `POST` | `/discord-bot/configure` |
| Status | `GET` | `/discord-bot/status` |
| List commands | `GET` | `/discord-bot/commands` |
| Create command | `POST` | `/discord-bot/command` |
| Moderate | `POST` | `/discord-bot/moderate` |
| Simulate command | `POST` | `/discord-bot/simulate-command` |
| Analyze | `POST` | `/discord-bot/analyze` |
| Analytics | `GET` | `/discord-bot/analytics` |
| Users | `GET` | `/discord-bot/users` |

`analyze` тратит квоту генераций; configure / moderate / simulate — управляющие хелперы.

## Примеры

```bash
curl -s -X POST http://localhost:8000/api/v1/level-designer \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{\"project_id\":\"$PID\",\"description\":\"Подводный храм с ловушками\"}" | jq .

curl -s -X POST http://localhost:8000/api/v1/character-creator \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"description":"Эльф-лучник в кожаной броне"}' | jq .

curl -s -X POST http://localhost:8000/api/v1/store-description \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"game_name":"Dungeon Explorer","platform":"steam","genre":"Action RPG","description":"Roguelike-данжены"}' | jq .

curl -s -X POST http://localhost:8000/api/v1/level-analyzer/compare \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"level_a":{...},"level_b":{...}}' | jq .
```

Texture upscaler обычно принимает `multipart/form-data` — точные поля в OpenAPI / UI.

## Квоты

Успешная генерация тратит квоту плана и даёт XP. Превышение → **402**.

## Rate limits

Auth и tool-роуты используют sliding window в Redis (fallback в память). При `APP_ENV=test` rate limiting **выключен**, чтобы CI проходил полный набор тестов.

## Асинхронные задачи

Upscale, character и sound могут уходить в Celery — дождитесь завершения worker перед скачиванием.
