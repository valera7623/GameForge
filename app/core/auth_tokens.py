"""Auth cookie helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from fastapi import Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token_raw,
    hash_token,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User

settings = get_settings()


def set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    common = {
        "httponly": True,
        "secure": settings.COOKIE_SECURE or settings.is_production,
        "samesite": settings.COOKIE_SAMESITE,
        "path": "/",
    }
    response.set_cookie(
        settings.ACCESS_COOKIE,
        access,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **common,
    )
    response.set_cookie(
        settings.REFRESH_COOKIE,
        refresh,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        **common,
    )


def clear_auth_cookies(response: Response) -> None:
    for name in (settings.ACCESS_COOKIE, settings.REFRESH_COOKIE):
        response.delete_cookie(name, path="/")


async def issue_tokens(db: AsyncSession, user: User) -> tuple[str, str]:
    """Create access JWT + rotate-capable refresh (DB-backed)."""
    jti = uuid4().hex
    raw = create_refresh_token_raw()
    expires = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(
        RefreshToken(
            user_id=user.id,
            jti=jti,
            token_hash=hash_token(raw),
            expires_at=expires,
        )
    )
    await db.flush()
    access = create_access_token(user.id, {"role": user.role.value})
    # Embed raw secret in JWT? Better: return opaque token = jti.raw
    refresh = f"{jti}.{raw}"
    return access, refresh


async def rotate_refresh(db: AsyncSession, refresh_token: str) -> tuple[User, str, str]:
    if "." not in refresh_token:
        raise ValueError("Invalid refresh token")
    jti, raw = refresh_token.split(".", 1)
    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
    row = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if (
        not row
        or row.revoked_at is not None
        or row.expires_at < now
        or row.token_hash != hash_token(raw)
    ):
        # Possible reuse — revoke all for this user if row exists
        if row:
            await db.execute(
                update(RefreshToken)
                .where(RefreshToken.user_id == row.user_id, RefreshToken.revoked_at.is_(None))
                .values(revoked_at=now)
            )
        raise ValueError("Invalid refresh token")

    row.revoked_at = now
    user_result = await db.execute(select(User).where(User.id == row.user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise ValueError("User not found")
    access, new_refresh = await issue_tokens(db, user)
    return user, access, new_refresh


async def revoke_refresh(db: AsyncSession, refresh_token: Optional[str], user_id: Optional[UUID] = None) -> None:
    now = datetime.now(timezone.utc)
    if refresh_token and "." in refresh_token:
        jti = refresh_token.split(".", 1)[0]
        await db.execute(
            update(RefreshToken).where(RefreshToken.jti == jti).values(revoked_at=now)
        )
    elif user_id:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
