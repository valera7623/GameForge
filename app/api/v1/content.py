"""Public CMS content API (published only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.schemas import ContentItemListOut, ContentItemOut, SitemapUrlOut, SitemapUrlsOut
from app.database import get_db
from app.models.content import ContentItem, ContentStatus
from app.services.markdown_html import md_to_html

router = APIRouter(prefix="/content", tags=["content"])


def _out(item: ContentItem) -> ContentItemOut:
    return ContentItemOut(
        id=item.id,
        kind=item.kind,
        slug=item.slug,
        locale=item.locale,
        title=item.title,
        body_md=item.body_md or "",
        body_html=md_to_html(item.body_md or ""),
        excerpt=item.excerpt,
        meta_title=item.meta_title,
        meta_description=item.meta_description,
        status=item.status,
        sort_order=item.sort_order,
        published_at=item.published_at,
        author_id=item.author_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def _list_published(
    db: AsyncSession, kind: str, locale: str, page: int, page_size: int
) -> ContentItemListOut:
    q = (
        select(ContentItem)
        .where(
            ContentItem.kind == kind,
            ContentItem.locale == locale,
            ContentItem.status == ContentStatus.PUBLISHED.value,
        )
        .order_by(ContentItem.sort_order, ContentItem.published_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(q)).scalars().all()
    return ContentItemListOut(items=[_out(r) for r in rows], total=len(rows), page=page, page_size=page_size)


@router.get("/faq", response_model=ContentItemListOut)
async def public_faq(
    locale: str = Query("en"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await _list_published(db, "faq", locale, page, page_size)


@router.get("/blog", response_model=ContentItemListOut)
async def public_blog(
    locale: str = Query("en"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await _list_published(db, "blog", locale, page, page_size)


@router.get("/blog/{slug}", response_model=ContentItemOut)
async def public_blog_post(
    slug: str,
    locale: str = Query("en"),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        select(ContentItem).where(
            ContentItem.kind == "blog",
            ContentItem.slug == slug,
            ContentItem.locale == locale,
            ContentItem.status == ContentStatus.PUBLISHED.value,
        )
    )
    item = row.scalar_one_or_none()
    if not item:
        raise HTTPException(404, detail="Not found")
    return _out(item)


@router.get("/pages/{slug}", response_model=ContentItemOut)
async def public_page(
    slug: str,
    locale: str = Query("en"),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        select(ContentItem).where(
            ContentItem.kind == "page",
            ContentItem.slug == slug,
            ContentItem.locale == locale,
            ContentItem.status == ContentStatus.PUBLISHED.value,
        )
    )
    item = row.scalar_one_or_none()
    if not item:
        raise HTTPException(404, detail="Not found")
    return _out(item)


@router.get("/sitemap-urls", response_model=SitemapUrlsOut)
async def sitemap_urls(db: AsyncSession = Depends(get_db)):
    domain = "https://gameforge.website"
    try:
        from app.services.platform_settings import get_general_settings

        general = await get_general_settings(db)
        d = (general.get("domain") or "gameforge.website").rstrip("/")
        domain = d if d.startswith("http") else f"https://{d}"
    except Exception:
        pass
    rows = (
        await db.execute(
            select(ContentItem).where(ContentItem.status == ContentStatus.PUBLISHED.value)
        )
    ).scalars().all()
    urls: list[SitemapUrlOut] = []
    # Always include FAQ index if any FAQ exists
    faq_locales = set()
    for item in rows:
        prefix = "/ru" if item.locale == "ru" else ""
        if item.kind == "faq":
            faq_locales.add(item.locale)
            continue
        if item.kind == "blog":
            loc = f"{domain}{prefix}/blog/post?slug={item.slug}"
        else:
            loc = f"{domain}{prefix}/page?slug={item.slug}"
        urls.append(
            SitemapUrlOut(
                loc=loc,
                lastmod=item.updated_at.date().isoformat() if item.updated_at else None,
            )
        )
    for loc_locale in faq_locales:
        prefix = "/ru" if loc_locale == "ru" else ""
        urls.append(SitemapUrlOut(loc=f"{domain}{prefix}/faq"))
    for loc_locale in {i.locale for i in rows if i.kind == "blog"}:
        prefix = "/ru" if loc_locale == "ru" else ""
        urls.append(SitemapUrlOut(loc=f"{domain}{prefix}/blog"))
    # unique
    seen = set()
    unique = []
    for u in urls:
        if u.loc not in seen:
            seen.add(u.loc)
            unique.append(u)
    return SitemapUrlsOut(urls=unique)


@router.get("/sitemap-cms.xml")
async def sitemap_cms_xml(db: AsyncSession = Depends(get_db)):
    data = await sitemap_urls(db)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u in data.urls:
        lines.append("<url>")
        lines.append(f"<loc>{u.loc}</loc>")
        if u.lastmod:
            lines.append(f"<lastmod>{u.lastmod}</lastmod>")
        lines.append("</url>")
    lines.append("</urlset>")
    return Response(content="\n".join(lines), media_type="application/xml")
