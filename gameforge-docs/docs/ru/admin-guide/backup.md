# Бэкапы

В prod Compose есть сервис профиля **`backup`**.

## Что делает

- `pg_dump` → gzip на volume `backup_data`
- Зеркало MinIO через `mc`
- Retention: **7 дней** (`BACKUP_KEEP_DAYS`)
- Интервал: `BACKUP_INTERVAL_SEC` (по умолчанию 86400)

## Включение

Remote deploy уже поднимает backup:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile backup up -d backup
```

Разовый запуск: `BACKUP_ONCE=1`.

## Offsite

Регулярно копируйте volume `/backups` во внешнее хранилище. Локальный retention — не disaster recovery.
