"""Admin CMS content CRUD."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.schemas import (
    ContentItemCreate,
    ContentItemListOut,
    ContentItemOut,
    ContentItemUpdate,
)
from app.core.rbac import require_permission
from app.database import get_db
from app.models.content import ContentItem, ContentKind, ContentStatus
from app.models.user import User
from app.services.markdown_html import md_to_html
from app.services.ops_logs import record_audit

router = APIRouter(prefix="/content")

VALID_KINDS = {k.value for k in ContentKind}
VALID_LOCALES = {"en", "ru"}


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


@router.get("", response_model=ContentItemListOut)
async def list_content(
    kind: Optional[str] = None,
    locale: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_permission("content:read")),
    db: AsyncSession = Depends(get_db),
):
    q = select(ContentItem)
    cq = select(func.count()).select_from(ContentItem)
    if kind:
        q = q.where(ContentItem.kind == kind)
        cq = cq.where(ContentItem.kind == kind)
    if locale:
        q = q.where(ContentItem.locale == locale)
        cq = cq.where(ContentItem.locale == locale)
    if status:
        q = q.where(ContentItem.status == status)
        cq = cq.where(ContentItem.status == status)
    total = (await db.execute(cq)).scalar() or 0
    rows = (
        await db.execute(
            q.order_by(ContentItem.sort_order, ContentItem.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return ContentItemListOut(items=[_out(r) for r in rows], total=total, page=page, page_size=page_size)


@router.post("", response_model=ContentItemOut)
async def create_content(
    body: ContentItemCreate,
    user: User = Depends(require_permission("content:write")),
    db: AsyncSession = Depends(get_db),
):
    if body.kind not in VALID_KINDS:
        raise HTTPException(400, detail="Invalid kind")
    if body.locale not in VALID_LOCALES:
        raise HTTPException(400, detail="Invalid locale")
    item = ContentItem(
        kind=body.kind,
        slug=body.slug.strip().lower().replace(" ", "-"),
        locale=body.locale,
        title=body.title,
        body_md=body.body_md,
        excerpt=body.excerpt,
        meta_title=body.meta_title,
        meta_description=body.meta_description,
        sort_order=body.sort_order,
        status=ContentStatus.DRAFT.value,
        author_id=user.id,
    )
    db.add(item)
    await db.flush()
    await record_audit(
        db,
        actor_id=user.id,
        action="content.create",
        target_type="content",
        target_id=str(item.id),
        meta={"kind": item.kind, "slug": item.slug},
    )
    return _out(item)


@router.get("/{item_id}", response_model=ContentItemOut)
async def get_content(
    item_id: UUID,
    user: User = Depends(require_permission("content:read")),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(ContentItem, item_id)
    if not item:
        raise HTTPException(404, detail="Not found")
    return _out(item)


@router.put("/{item_id}", response_model=ContentItemOut)
async def update_content(
    item_id: UUID,
    body: ContentItemUpdate,
    user: User = Depends(require_permission("content:write")),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(ContentItem, item_id)
    if not item:
        raise HTTPException(404, detail="Not found")
    data = body.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"]:
        data["slug"] = data["slug"].strip().lower().replace(" ", "-")
    if "locale" in data and data["locale"] not in VALID_LOCALES:
        raise HTTPException(400, detail="Invalid locale")
    for k, v in data.items():
        setattr(item, k, v)
    await db.flush()
    await record_audit(
        db,
        actor_id=user.id,
        action="content.update",
        target_type="content",
        target_id=str(item.id),
    )
    return _out(item)


@router.delete("/{item_id}")
async def delete_content(
    item_id: UUID,
    user: User = Depends(require_permission("content:write")),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(ContentItem, item_id)
    if not item:
        raise HTTPException(404, detail="Not found")
    await db.delete(item)
    await record_audit(
        db,
        actor_id=user.id,
        action="content.delete",
        target_type="content",
        target_id=str(item_id),
    )
    return {"ok": True, "id": str(item_id)}


@router.post("/{item_id}/publish", response_model=ContentItemOut)
async def publish_content(
    item_id: UUID,
    user: User = Depends(require_permission("content:write")),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(ContentItem, item_id)
    if not item:
        raise HTTPException(404, detail="Not found")
    item.status = ContentStatus.PUBLISHED.value
    item.published_at = datetime.now(timezone.utc)
    await db.flush()
    await record_audit(
        db,
        actor_id=user.id,
        action="content.publish",
        target_type="content",
        target_id=str(item.id),
    )
    return _out(item)


@router.post("/{item_id}/unpublish", response_model=ContentItemOut)
async def unpublish_content(
    item_id: UUID,
    user: User = Depends(require_permission("content:write")),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(ContentItem, item_id)
    if not item:
        raise HTTPException(404, detail="Not found")
    item.status = ContentStatus.DRAFT.value
    await db.flush()
    await record_audit(
        db,
        actor_id=user.id,
        action="content.unpublish",
        target_type="content",
        target_id=str(item.id),
    )
    return _out(item)
