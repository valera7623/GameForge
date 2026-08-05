# AI models and costs

**`/admin/ai-models`** shows estimated AI spend and editable pricing (JSON in `platform_settings` key `ai_models`).

| Action | Permission |
|--------|------------|
| View pricing / costs | `dashboard:read` (all staff) |
| Edit pricing | `settings:write` (`super_admin` only) |

Generations store `cost_usd`, `prompt_tokens`, `completion_tokens`, `model_name`, `duration_ms`, and `client_ip`. Costs are computed from token usage × rates (or per-call rates for image/audio providers).
