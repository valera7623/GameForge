# Content CMS

Staff manage FAQ, blog posts, and SEO pages at **`/admin/content`**.

| Permission | Roles |
|------------|-------|
| `content:read` | all staff |
| `content:write` | `super_admin`, `admin`, `manager` |

Public URLs (published only):

- `/faq`, `/ru/faq`
- `/blog`, `/ru/blog`
- `/blog/post?slug=…`, `/ru/blog/post?slug=…`

API:

- Admin: `/api/v1/admin/content`
- Public: `/api/v1/content/faq|blog|pages/{slug}`
- CMS sitemap: `/api/v1/content/sitemap-cms.xml` (also listed in `robots.txt`)
