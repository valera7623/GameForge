"""Record audit / error / API logs and purge old rows."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.ops_log import ApiRequestLog, AuditLog, ErrorLog

RETENTION_DAYS = 30


async def record_audit(
    db: AsyncSession,
    *,
    actor_id: Optional[UUID],
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    meta: Optional[dict[str, Any]] = None,
    ip: Optional[str] = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            meta=meta or {},
            ip=ip,
        )
    )
    await db.flush()


async def record_error(
    db: AsyncSession,
    *,
    source: str,
    message: str,
    status_code: Optional[int] = None,
    path: Optional[str] = None,
    user_id: Optional[UUID] = None,
    generation_id: Optional[UUID] = None,
    request_id: Optional[str] = None,
) -> None:
    db.add(
        ErrorLog(
            source=source,
            message=message[:4000],
            status_code=status_code,
            path=path,
            user_id=user_id,
            generation_id=generation_id,
            request_id=request_id,
        )
    )
    await db.flush()


def record_error_sync(
    session: Session,
    *,
    source: str,
    message: str,
    status_code: Optional[int] = None,
    path: Optional[str] = None,
    user_id: Optional[UUID] = None,
    generation_id: Optional[UUID] = None,
    request_id: Optional[str] = None,
) -> None:
    session.add(
        ErrorLog(
            source=source,
            message=message[:4000],
            status_code=status_code,
            path=path,
            user_id=user_id,
            generation_id=generation_id,
            request_id=request_id,
        )
    )


async def record_api_request(
    db: AsyncSession,
    *,
    method: str,
    path: str,
    status_code: int,
    duration_ms: int,
    user_id: Optional[UUID] = None,
    ip: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    db.add(
        ApiRequestLog(
            method=method,
            path=path[:512],
            status_code=status_code,
            duration_ms=duration_ms,
            user_id=user_id,
            ip=ip,
            request_id=request_id,
        )
    )
    await db.flush()


async def purge_ops_logs(db: AsyncSession, days: int = RETENTION_DAYS) -> dict[str, int]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    counts: dict[str, int] = {}
    for model, name in (
        (AuditLog, "audit"),
        (ErrorLog, "errors"),
        (ApiRequestLog, "api"),
    ):
        result = await db.execute(delete(model).where(model.created_at < cutoff))
        counts[name] = result.rowcount or 0
    await db.flush()
    return counts


def purge_ops_logs_sync(session: Session, days: int = RETENTION_DAYS) -> dict[str, int]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    counts: dict[str, int] = {}
    for model, name in (
        (AuditLog, "audit"),
        (ErrorLog, "errors"),
        (ApiRequestLog, "api"),
    ):
        result = session.execute(delete(model).where(model.created_at < cutoff))
        counts[name] = result.rowcount or 0
    return counts
