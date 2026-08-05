<p align="center">
  <img src=".github/assets/logo.png" alt="GameForge" width="280">
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11+-blue" alt="Python"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.115+-green" alt="FastAPI"></a>
  <a href="https://docs.docker.com/compose/"><img src="https://img.shields.io/badge/docker-compose-24+-blue" alt="Docker"></a>
  <a href="https://github.com/valera7623/GameForge/actions/workflows/ci.yml"><img src="https://github.com/valera7623/GameForge/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <strong>Русский</strong>
</p>

<p align="center">
  <a href="https://docs.gameforge.website/ru/">Документация</a> ·
  <a href="https://gameforge.website">Production</a> ·
  <a href="https://github.com/valera7623/GameForge/issues">Issues</a>
</p>

---

## Оглавление

- [О проекте](#о-проекте)
- [Живой сайт](#живой-сайт)
- [Возможности](#возможности)
- [Быстрый старт](#быстрый-старт)
- [Архитектура](#архитектура)
- [Тарифы и биллинг](#тарифы-и-биллинг)
- [Документация](#документация)
- [Вклад в проект](#вклад-в-проект)
- [Команда](#команда)
- [Лицензия](#лицензия)

---

## О проекте

**GameForge** — открытый **AI Game Dev Toolkit**: четырнадцать ИИ-инструментов для инди, студий и моддеров — уровни, квесты, текстуры, персонажи, звук, плейтест, локализация, баланс, анализ уровней, тексты витрин, инсайты плейтеста, сценарии трейлеров, анализ отзывов и Discord — с проектами, командными местами и ZIP-экспортом в Unity, Unreal или Godot.

### Проблема

Команды тратят время на рутину контента:

- Тайлмапы, квесты и таблицы локализации собираются вручную
- Пайплайны текстур / персонажей / звука размазаны по разным тулам
- Бюджет инди не всегда тянет живые AI API на этапе прототипа

### Решение

| Направление | Что даёт GameForge |
|-------------|-------------------|
| **Четырнадцать AI-tools** | От level/quest до store copy, трейлеров, отзывов и Discord |
| **Проекты и экспорт** | Ассеты по тайтлу + ZIP |
| **Mock или реальный AI** | `USE_MOCK_AI=true` без оплаты; ProxyAPI / OpenAI когда нужно |
| **Команда и тарифы** | Free / Indie / Studio / Enterprise (on-prem) |
| **Прод-стек** | Caddy HTTPS, MinIO `/s3/`, Celery, CI-gated deploy |

---

## Живой сайт

**Production:** [https://gameforge.website](https://gameforge.website)

**Документация:** [https://docs.gameforge.website/ru/](https://docs.gameforge.website/ru/) · [EN](https://docs.gameforge.website/)

Локальные демо-аккаунты (после seed — **не** для продакшена):

| Роль | Email | Пароль |
|------|-------|--------|
| User | `demo@gamedev.ai` | `demo123456` |
| Admin | `admin@gamedev.ai` | `admin123456` |

> Seed запрещён при `APP_ENV=production`.

---

## Возможности

| Возможность | Описание |
|-------------|----------|
| **Level Designer** | Текст → tilemap JSON + canvas |
| **Quest Generator** | Цели, диалоги, ветвления JSON |
| **Texture Upscaler** | PNG 2× / 4× (Real-ESRGAN или PIL mock) |
| **Character Creator** | Концепт-арт по описанию |
| **Sound Designer** | SFX / музыка / голос (WAV/MP3) |
| **Playtester** | QA-отчёт по дизайн-доку |
| **Localization** | Переводы JSON/CSV |
| **Game Balancer** | Метрики баланса боя / экономики |
| **Level Analyzer** | Pathfinding, сложность, сравнение уровней |
| **Store Description** | Тексты Steam / App Store / Google Play |
| **Playtest Analyzer** | Retention и инсайты по сессиям |
| **Trailer Script** | Сценарии launch / teaser / gameplay |
| **Review Analyzer** | Sentiment и кластеры проблем в отзывах |
| **Discord Bot** | Community bot studio (API / simulate MVP) |
| **Projects** | Проекты по движку + ZIP |
| **Team seats** | Организации Studio, инвайты |
| **Геймификация** | XP, ачивки, monthly leaderboard |
| **i18n UI** | English + Русский, светлая/тёмная тема |
| **Биллинг** | Stripe / YuKassa (или `DISABLE_BILLING=true`) |

---

## Быстрый старт

### Docker Compose (рекомендуется)

```bash
git clone https://github.com/valera7623/GameForge.git
cd GameForge

cp .env.example .env
docker compose up -d --build
docker compose exec api python scripts/seed_db.py

curl -s http://localhost:8000/api/v1/health
curl -s http://localhost:8000/api/v1/health/ready
```

Или: `./scripts/deploy.sh`

| Сервис | URL |
|--------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger (не production) | http://localhost:8000/docs |
| MinIO | http://localhost:9001 |

### Hot-reload фронтенда

```bash
docker compose --profile dev up frontend-dev
# → http://localhost:5173
```

### Реальные AI-провайдеры

```env
USE_MOCK_AI=false
OPENAI_API_KEY=your_proxyapi_key
OPENAI_BASE_URL=https://api.proxyapi.ru/openai/v1
OPENAI_MODEL=gpt-4o
```

Ключ из [ProxyAPI](https://proxyapi.ru) / AITunnel. Опционально: `STABILITY_API_KEY` + `IMAGE_PROVIDER=stability`, `STABILITY_AUDIO_MODEL=stable-audio-2.5` (Sound Designer), `REALESRGAN_URL=http://realesrgan:8080` (CPU Real-ESRGAN ncnn/llvmpipe), `REPLICATE_API_TOKEN`, `ELEVENLABS_API_KEY`.

```bash
docker compose --profile ai up -d --build realesrgan
```

### Production (VPS + Caddy)

```bash
# DNS: @, www, docs → A <VPS_IP>
# Заполните .env по Production checklist в .env.example

docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile backup up -d --build
# или на сервере: ./scripts/deploy_remote.sh
```

| Переменная | Заметки |
|------------|---------|
| `APP_ENV=production` | Жёсткая валидация настроек |
| `USE_MOCK_AI` | `true` без трат на AI; `false` + ключ для живых моделей |
| `DISABLE_BILLING` | `true`, пока нет Stripe/YuKassa |
| `EMAIL_PROVIDER` | `resend` или `smtp` |
| `S3_PUBLIC_ENDPOINT` | `https://<domain>/s3` |

Деплой: GitHub Actions **Deploy** после зелёного **CI**. Подробнее: [docs → VPS](https://docs.gameforge.website/ru/deployment/vps/).

### On-prem (Enterprise)

```bash
docker compose -f docker-compose.yml -f docker-compose.onprem.yml up -d
```

### Пример API

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@gamedev.ai","password":"demo123456"}' | jq -r .access_token)

curl -s -X POST http://localhost:8000/api/v1/character-creator \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"description":"Эльф-лучник в кожаной броне"}' | jq .
```

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                     GameForge (v1.2.0)                        │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Vite MPA + Nginx)  │  FastAPI /api/v1  │  Celery │
├───────────────────────────────┴───────────────────┴─────────┤
│  AI tools (mock или OpenAI / Real-ESRGAN / MusicGen / …)    │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL  │  Redis (rate limit, broker)  │  MinIO (S3)   │
└─────────────────────────────────────────────────────────────┘
         ▲ Caddy + Let's Encrypt (production) · публичный /s3/
```

**Стек:** FastAPI · SQLAlchemy · Alembic · PostgreSQL 15 · Redis 7 · Celery · MinIO · Vite · Nginx · Caddy

---

## Тарифы и биллинг

| План | Цена | Генераций / месяц |
|------|------|-------------------|
| Free | $0 | 5 |
| Indie | $19 | 100 |
| Studio | $99 | 1000 |
| Enterprise | custom | unlimited / on-prem |

В production без ключей оплаты: `DISABLE_BILLING=true`. Локально mock-апгрейды — при `ALLOW_MOCK_BILLING=true`.

---

## Документация

| Раздел | Описание |
|--------|----------|
| [User Guide](https://docs.gameforge.website/ru/user-guide/) | Dashboard, инструменты, команда, биллинг |
| [Admin Guide](https://docs.gameforge.website/ru/admin-guide/) | Чеклист prod, мониторинг, бэкапы |
| [Developer Guide](https://docs.gameforge.website/ru/developer-guide/) | API, auth, эндпоинты |
| [Архитектура](https://docs.gameforge.website/ru/architecture/) | Компоненты и потоки |
| [Развёртывание](https://docs.gameforge.website/ru/deployment/) | Docker, VPS, troubleshooting |

Локально (MkDocs Material, EN/RU):

```bash
cd gameforge-docs && ./mkdocs.sh serve
# → http://127.0.0.1:8001
```

---

## Вклад в проект

Issues, PR и фидбек приветствуются.

1. Fork → `git checkout -b feature/my-feature`
2. Код + тесты + docs
3. `ruff check app tests` и `pytest -q` (нужны Postgres + Redis; при `APP_ENV=test` rate limit отключён)
4. Откройте Pull Request

CI (`.github/workflows/ci.yml`) на каждый push в `main`: ruff, pytest, сборка frontend, проверка Compose config.

---

## Команда

| Имя | Роль | Контакт |
|-----|------|---------|
| **Valeriy Popov** | Founder & Lead Developer | [GitHub](https://github.com/valera7623) · [valera7623@gmail.com](mailto:valera7623@gmail.com) |

---

## Лицензия

[MIT License](LICENSE) © 2026 Valeriy Popov

---

## Поддержка

- Поставьте ★ репозиторию на [GitHub](https://github.com/valera7623/GameForge)
- [Сообщить о баге](https://github.com/valera7623/GameForge/issues)
- Документация: [https://docs.gameforge.website/ru/](https://docs.gameforge.website/ru/)

---

<p align="center">
  <strong>GameForge v1.2.0</strong> — четырнадцать ИИ-инструментов для геймдева<br>
  Для инди, студий и моддеров, которые хотят шипить быстрее
</p>
