# KPI dashboard (weekly)

Update every Monday. Sources: Metrika/GA4 + DB registrations + this CSV.

| Week | LocForge visits | Reg `from=locforge` | First Translate | Paying (pack/sub) | Outreach sent | Replies | Notes |
|------|-----------------|---------------------|-----------------|-------------------|---------------|---------|-------|
| 1 | | | | | | | |
| 2 | | | | | | | |
| 3 | | | | | | | |
| 4 | | | | | | | |
| … | | | | | | | |
| 12 | | | | | | | |

## Targets

| Metric | D30 | D90 |
|--------|-----|-----|
| Visits locforge | 1 500 | 6 000 |
| Reg from=locforge | 40 | 150 |
| First Translate | 20 | 80 |
| Paying | 3 | 12 |
| Named case | 0 | 1 |

## SQL helpers (prod)

```sql
-- Registrations from LocForge
SELECT date_trunc('week', created_at) AS week, count(*)
FROM users WHERE signup_source = 'locforge'
GROUP BY 1 ORDER BY 1;

-- Pack interest at signup
SELECT signup_pack, count(*) FROM users
WHERE signup_source = 'locforge' GROUP BY 1;
```
