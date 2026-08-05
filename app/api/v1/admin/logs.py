"""Admin ops logs — audit / errors / API request logs."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.schemas import (
    ApiRequestLogListOut,
    ApiRequestLogOut,
    AuditLogListOut,
    AuditLogOut,
    ErrorLogListOut,
    ErrorLogOut,
    PurgeLogsOut,
)
from app.core.rbac import require_permission
from app.database import get_db
from app.models.ops_log import ApiRequestLog, AuditLog, ErrorLog
from app.models.user import User
from app.services.ops_logs import purge_ops_logs, record_audit

router = APIRouter(prefix="/logs")


@router.get("/audit", response_model=AuditLogListOut)
async def list_audit(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    action: Optional[str] = None,
    user: User = Depends(require_permission("logs:read")),
    db: AsyncSession = Depends(get_db),
):
    q = select(AuditLog)
    cq = select(func.count()).select_from(AuditLog)
    if action:
        q = q.where(AuditLog.action == action)
        cq = cq.where(AuditLog.action == action)
    total = (await db.execute(cq)).scalar() or 0
    rows = (
        await db.execute(q.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()
    return AuditLogListOut(
        items=[
            AuditLogOut(
                id=r.id,
                actor_id=r.actor_id,
                action=r.action,
                target_type=r.target_type,
                target_id=r.target_id,
                meta=r.meta or {},
                ip=r.ip,
                created_at=r.created_at,
            )
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/errors", response_model=ErrorLogListOut)
async def list_errors(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    source: Optional[str] = None,
    user: User = Depends(require_permission("logs:read")),
    db: AsyncSession = Depends(get_db),
):
    q = select(ErrorLog)
    cq = select(func.count()).select_from(ErrorLog)
    if source:
        q = q.where(ErrorLog.source == source)
        cq = cq.where(ErrorLog.source == source)
    total = (await db.execute(cq)).scalar() or 0
    rows = (
        await db.execute(q.order_by(ErrorLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()
    return ErrorLogListOut(
        items=[
            ErrorLogOut(
                id=r.id,
                source=r.source,
                message=r.message,
                status_code=r.status_code,
                path=r.path,
                user_id=r.user_id,
                generation_id=r.generation_id,
                request_id=r.request_id,
                created_at=r.created_at,
            )
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/api", response_model=ApiRequestLogListOut)
async def list_api_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    path: Optional[str] = None,
    status_code: Optional[int] = None,
    user: User = Depends(require_permission("logs:read")),
    db: AsyncSession = Depends(get_db),
):
    q = select(ApiRequestLog)
    cq = select(func.count()).select_from(ApiRequestLog)
    if path:
        q = q.where(ApiRequestLog.path.contains(path))
        cq = cq.where(ApiRequestLog.path.contains(path))
    if status_code is not None:
        q = q.where(ApiRequestLog.status_code == status_code)
        cq = cq.where(ApiRequestLog.status_code == status_code)
    total = (await db.execute(cq)).scalar() or 0
    rows = (
        await db.execute(
            q.order_by(ApiRequestLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()
    return ApiRequestLogListOut(
        items=[
            ApiRequestLogOut(
                id=r.id,
                method=r.method,
                path=r.path,
                status_code=r.status_code,
                duration_ms=r.duration_ms,
                user_id=r.user_id,
                ip=r.ip,
                request_id=r.request_id,
                created_at=r.created_at,
            )
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/purge", response_model=PurgeLogsOut)
async def purge_logs(
    user: User = Depends(require_permission("settings:write")),
    db: AsyncSession = Depends(get_db),
):
    deleted = await purge_ops_logs(db)
    await record_audit(db, actor_id=user.id, action="logs.purge", meta=deleted)
    return PurgeLogsOut(deleted=deleted)
