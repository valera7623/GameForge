# ИИ-модели и расходы

**`/admin/ai-models`** — оценка расходов и прайс (ключ `ai_models` в `platform_settings`).

| Действие | Право |
|----------|-------|
| Просмотр | `dashboard:read` |
| Правка прайса | `settings:write` (только `super_admin`) |

У генераций пишутся `cost_usd`, токены, `model_name`, `duration_ms`, `client_ip`.
