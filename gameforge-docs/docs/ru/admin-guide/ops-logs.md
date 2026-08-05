# Операционные логи

**`/admin/logs`** — audit / errors / api **без тел запросов**.

Хранение **30 дней**. Celery beat `tasks.purge_ops_logs` чистит старое; super_admin может запустить purge из UI.
