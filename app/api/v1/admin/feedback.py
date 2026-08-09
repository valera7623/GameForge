"""Admin feedback inbox API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.core.rbac import require_permission
from app.models.feedback import FeedbackCategory, FeedbackMessage, FeedbackStatus
from app.models.user import User

router = APIRouter(prefix="/feedback", tags=["admin-feedback"])


class FeedbackOut(BaseModel):
    id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    category: str
    subject: str
    message: str
    email: Optional[str] = None
    status: str
    page_url: Optional[str] = None
    client_ip: Optional[str] = None
    admin_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class FeedbackListOut(BaseModel):
    items: list[FeedbackOut]
    total: int
    page: int
    per_page: int


class FeedbackPatchRequest(BaseModel):
    status: Optional[str] = Field(default=None, pattern="^(new|read|closed)$")
    admin_note: Optional[str] = Field(default=None, max_length=2000)


def _out(row: FeedbackMessage) -> FeedbackOut:
    return FeedbackOut(
        id=str(row.id),
        user_id=str(row.user_id) if row.user_id else None,
        user_email=row.user.email if row.user else None,
        category=row.category.value,
        subject=row.subject or "",
        message=row.message,
        email=row.email,
        status=row.status.value,
        page_url=row.page_url,
        client_ip=row.client_ip,
        admin_note=row.admin_note,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=FeedbackListOut)
async def list_feedback(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    _: User = Depends(require_permission("feedback:read")),
    db: AsyncSession = Depends(get_db),
):
    q = select(FeedbackMessage).options(selectinload(FeedbackMessage.user))
    count_q = select(func.count()).select_from(FeedbackMessage)

    if status_filter:
        try:
            st = FeedbackStatus(status_filter)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
        q = q.where(FeedbackMessage.status == st)
        count_q = count_q.where(FeedbackMessage.status == st)

    if category:
        try:
            cat = FeedbackCategory(category)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid category")
        q = q.where(FeedbackMessage.category == cat)
        count_q = count_q.where(FeedbackMessage.category == cat)

    total = (await db.execute(count_q)).scalar_one()
    rows = (
        await db.execute(
            q.order_by(FeedbackMessage.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).scalars().all()

    return FeedbackListOut(
        items=[_out(r) for r in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.patch("/{feedback_id}", response_model=FeedbackOut)
async def patch_feedback(
    feedback_id: UUID,
    body: FeedbackPatchRequest,
    _: User = Depends(require_permission("feedback:write")),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            select(FeedbackMessage)
            .where(FeedbackMessage.id == feedback_id)
            .options(selectinload(FeedbackMessage.user))
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")

    if body.status is not None:
        row.status = FeedbackStatus(body.status)
    if body.admin_note is not None:
        row.admin_note = body.admin_note.strip()[:2000]

    await db.flush()
    await db.refresh(row)
    return _out(row)
