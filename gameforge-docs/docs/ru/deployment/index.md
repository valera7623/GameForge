# Развёртывание

Локальный Docker и production VPS.

## Содержание

| Страница | Темы |
|----------|------|
| [Docker](docker.md) | Compose-профили, локальный стек |
| [VPS](vps.md) | Caddy, DNS, публичный S3, CI |
| [Устранение неполадок](troubleshooting.md) | Частые проблемы |

## Режимы

| Режим | Compose | Заметки |
|-------|---------|---------|
| Local | `docker-compose.yml` | Открытые порты; mock AI OK |
| Production | `+ docker-compose.prod.yml` | Caddy, migrate, без host-портов API |
| On-prem | `+ docker-compose.onprem.yml` | Enterprise plan, биллинг выкл. |
