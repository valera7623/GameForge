# Ops logs

**`/admin/logs`** — three tabs, no request bodies:

1. **Audit** — admin mutations (`user.block`, `tool.toggle`, `content.publish`, …)
2. **Errors** — API 5xx and failed generations
3. **API** — brief request log (`method`, `path`, `status`, `duration_ms`, `user_id`, `ip`)

Retention: **30 days**. Daily Celery beat task `tasks.purge_ops_logs` deletes older rows. Super-admin can also **Purge old** from the UI (`POST /api/v1/admin/logs/purge`).
