# Инструменты

В GameForge **четырнадцать** ИИ-инструментов. При `USE_MOCK_AI=true` ключи не нужны; при `false` вызываются внешние провайдеры.

Маркетинговые страницы: `/tools/<slug>` (EN) и `/ru/tools/<slug>` (RU). Редакторы в приложении: `https://gameforge.website/<slug>` после входа.

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

## Game Balancer

- **Вход:** игровые данные (классы, оружие, экономика в JSON)
- **Выход:** метрики баланса, выбросы, рекомендации по тюнингу
- **API:** `POST /api/v1/game-balancer`

## Level Analyzer

- **Вход:** данные уровня / пути для анализа сложности и достижимости
- **Выход:** pathfinding, сигналы сложности, «узкие места»
- **API:** `POST /api/v1/level-analyzer`
- **Сравнение:** `POST /api/v1/level-analyzer/compare` — два уровня рядом

## Store Description

- **Вход:** бриф игры, платформа (Steam / App Store / Google Play), тон, язык
- **Выход:** текст витрины (название, short/long description, теги, keywords)
- **API:** `POST /api/v1/store-description`
- Язык UI (`gf_lang`) влияет на язык ответа, если интерфейс на русском

## Playtest Analyzer

- **Вход:** метрики сессий / заметки по фидбеку
- **Выход:** инсайты по retention, точки трения, приоритетные рекомендации
- **API:** `POST /api/v1/playtest-analyzer`

!!! note "Playtester и Playtest Analyzer"
    **Playtester** — разбор дизайн-дока *до* билда. **Playtest Analyzer** — разбор телеметрии и фидбека *после* сессий.

## Trailer Script

- **Вход:** питч игры, тип трейлера (launch / teaser / gameplay), длительность, тон
- **Выход:** тайминг сцен, voiceover, оверлеи, заметки по звуку
- **API:** `POST /api/v1/trailer-script`

## Review Analyzer

- **Вход:** отзывы игроков (текст, опционально рейтинг / язык)
- **Выход:** sentiment, повторяющиеся проблемы, кластеры тем
- **API:** `POST /api/v1/review-analyzer`

## Discord Bot (studio)

Настройка community-бота (токен шифруется), команды, модерация и аналитика. Это набор эндпоинтов, а не один POST.

| Действие | Метод | Путь |
|----------|-------|------|
| Сохранить конфиг | `POST` | `/api/v1/discord-bot/configure` |
| Статус | `GET` | `/api/v1/discord-bot/status` |
| Список команд | `GET` | `/api/v1/discord-bot/commands` |
| Создать команду | `POST` | `/api/v1/discord-bot/command` |
| Модерация | `POST` | `/api/v1/discord-bot/moderate` |
| Симуляция команды | `POST` | `/api/v1/discord-bot/simulate-command` |
| Анализ сообщества | `POST` | `/api/v1/discord-bot/analyze` |
| Аналитика | `GET` | `/api/v1/discord-bot/analytics` |
| Пользователи | `GET` | `/api/v1/discord-bot/users` |

В дефолтном деплое **нет** живого Discord gateway worker — модерация и команды это API/simulate MVP. Токены хранятся в Fernet-шифровании.

## URL ассетов

Файлы в MinIO. В проде браузер открывает **signed** URL вида `https://<domain>/s3/...`. При ошибках см. [VPS](../deployment/vps.md).
