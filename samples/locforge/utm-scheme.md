# LocForge / GameForge UTM scheme

Use on every outbound link. First-touch is stored in `localStorage` (`gf_attribution`) and persisted on register (`users.attribution`).

## Parameters

| Param | Values |
|-------|--------|
| `utm_source` | `reddit`, `discord`, `tg`, `vk`, `habr`, `itch`, `steam`, `x`, `bluesky`, `email`, `locforge` |
| `utm_medium` | `dm`, `comment`, `post`, `hero`, `nav`, `pricing`, `case`, `reel`, `ads` |
| `utm_campaign` | `lf_ru`, `lf_en`, `lf_ru_pilot`, `lf_en_pilot`, `gf_upsell_d90` |
| `utm_content` | pack id (`starter`/`indie`/`studio`) or hook id (`hook_a`/`hook_b`/`hook_c`) |
| `from` | `locforge` (product source for signup) |
| `pack` | `starter` / `indie` / `studio` (maps to `loc_*` billing plans) |

## Canonical LocForge landing links

```
https://gameforge.website/ru/locforge?utm_source=tg&utm_medium=post&utm_campaign=lf_ru
https://gameforge.website/en/locforge?utm_source=reddit&utm_medium=comment&utm_campaign=lf_en
https://gameforge.website/register?from=locforge&next=/localization&pack=starter&utm_source=discord&utm_medium=dm&utm_campaign=lf_en
```

## Goals (GA4 event / Metrika reachGoal)

| Goal | When |
|------|------|
| `sign_up` | Successful registration |
| `localize_success` | Successful Translate |
| `loc_pack_click` | Word-pack checkout click |
| `loc_sample_loaded` | Ashen Hollow sample loaded |
| `locforge_cta` | Optional: CTA click on landing |

## Weekly KPI sheet

See [kpi-dashboard.md](kpi-dashboard.md).
