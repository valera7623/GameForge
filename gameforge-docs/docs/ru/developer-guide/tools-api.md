# Эндпоинты инструментов

Все маршруты под `/api/v1`, нужна аутентификация (если не указано иное).

| Инструмент | Метод | Путь |
|------------|-------|------|
| Level Designer | `POST` | `/level-designer` |
| Quest Generator | `POST` | `/quest-generator` |
| Texture Upscaler | `POST` | `/texture-upscaler` |
| Character Creator | `POST` | `/character-creator` |
| Sound Designer | `POST` | `/sound-designer` |
| Playtester | `POST` | `/playtester` |
| Localization | `POST` | `/localization` |

## Примеры

```bash
curl -s -X POST http://localhost:8000/api/v1/level-designer \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{\"project_id\":\"$PID\",\"description\":\"Подводный храм с ловушками\"}" | jq .

curl -s -X POST http://localhost:8000/api/v1/character-creator \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"description":"Эльф-лучник в кожаной броне"}' | jq .
```

Texture upscaler обычно принимает `multipart/form-data` — точные поля в OpenAPI / UI.

## Квоты

Успешная генерация тратит квоту плана и даёт XP. Превышение → **402**.

## Асинхронные задачи

Upscale, character и sound могут уходить в Celery — дождитесь завершения worker перед скачиванием.
