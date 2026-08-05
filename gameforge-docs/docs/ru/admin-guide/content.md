# CMS контент

Сотрудники управляют FAQ, блогом и SEO-страницами в **`/admin/content`**.

| Право | Роли |
|-------|------|
| `content:read` | весь staff |
| `content:write` | `super_admin`, `admin`, `manager` |

Публичные URL (только published):

- `/faq`, `/ru/faq`
- `/blog`, `/ru/blog`
- `/blog/post?slug=…`, `/ru/blog/post?slug=…`

API: `/api/v1/admin/content`, публично `/api/v1/content/*`, sitemap `/api/v1/content/sitemap-cms.xml`.
