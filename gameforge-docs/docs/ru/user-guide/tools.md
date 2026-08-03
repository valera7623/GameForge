# Инструменты

В GameForge **семь** ИИ-инструментов. При `USE_MOCK_AI=true` ключи не нужны; при `false` вызываются внешние провайдеры.

## Level Designer

- **Вход:** текстовый бриф уровня
- **Выход:** tilemap JSON + canvas
- **API:** `POST /api/v1/level-designer`

## Quest Generator

- **Вход:** промпт квеста / сюжета
- **Выход:** структура квеста и диалоги JSON
- **API:** `POST /api/v1/quest-generator`

## Texture Upscaler

- **Вход:** изображение + масштаб 2× / 4×
- **Выход:** PNG URL (Real-ESRGAN или PIL)
- **API:** `POST /api/v1/texture-upscaler`
- Тяжёлая работа может идти в **Celery worker**

## Character Creator

- **Вход:** описание персонажа (обязательно)
- **Выход:** URL изображения
- **API:** `POST /api/v1/character-creator`

## Sound Designer

- **Вход:** промпт + kind (sfx / music / voice)
- **Выход:** URL аудио
- **API:** `POST /api/v1/sound-designer`

## Playtester

- **Вход:** дизайн-док / описание фичи
- **Выход:** QA-отчёт JSON
- **API:** `POST /api/v1/playtester`

## Localization

- **Вход:** строки / JSON + целевые языки
- **Выход:** JSON или CSV переводов
- **API:** `POST /api/v1/localization`

## URL ассетов

Файлы в MinIO. В проде браузер открывает **signed** URL вида `https://<domain>/s3/...`. При ошибках см. [VPS](../deployment/vps.md).
