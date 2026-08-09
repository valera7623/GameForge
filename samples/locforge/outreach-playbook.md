# LocForge outreach playbook (D1–30)

**Cadence:** 10 touches/day · 5 days/week · update [outreach-leads.csv](outreach-leads.csv) after each batch.

## Rules

1. Value first — never cold-spam Discord/Reddit channels.
2. DM only after public intent (loc ask, EN-only Steam page, CSV thread).
3. Offer free pilot: RU/ES/DE + glossary + length QA; ask permission to name the game.
4. Always use UTM links from [utm-scheme.md](utm-scheme.md).
5. Max 1 follow-up if no reply in 5 days.

## Daily checklist

- [ ] Pick 10 rows with `status=ready` (mix RU + EN)
- [ ] Personalize first line (game name / engine / post)
- [ ] Send with correct template (`dm_en` / `dm_ru` / `comment_en`)
- [ ] Set `sent_at`, `status=sent`, `utm_campaign`
- [ ] Log replies same day (`reply=yes|maybe|no`)

## Templates

### DM EN (`dm_en`)

```
Hey — saw your {game / post}. LocForge localizes indie CSV in one evening (glossary + UI length QA + Unity/Godot export).

Happy to run a free pilot on your strings (RU/ES/DE). If it helps and you are ok with it, we can feature the game on the case page.

Link: https://gameforge.website/en/locforge?utm_source={channel}&utm_medium=dm&utm_campaign=lf_en
Or just reply with a CSV.
```

### DM RU (`dm_ru`)

```
Привет! Увидел {игру / пост}. LocForge — локализация инди CSV за один вечер: глоссарий, QA длины UI, экспорт Unity/Godot.

Могу сделать бесплатный пилот (RU/ES/DE). Если ок — укажем игру в кейсе на лендинге.

https://gameforge.website/ru/locforge?utm_source={channel}&utm_medium=dm&utm_campaign=lf_ru
Или просто пришлите CSV в ответ.
```

### Public comment EN (`comment_en`)

```
If you already have key,source CSV, LocForge does glossary + length QA + Unity/Godot export without a bureau — useful before Steam multilingual. Happy to pilot for free if you DM a sample.
```

### Follow-up (day 5)

```
Quick bump — still happy to run that free LocForge pilot on your CSV if useful. No pressure either way.
```

## Status values

`ready` → `sent` → `replied` / `pilot` / `won` / `lost` / `skip`
