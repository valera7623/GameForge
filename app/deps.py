"""FastAPI dependencies: auth, DB, generation quota."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.security import decode_token, verify_api_key
from app.database import get_db
from app.models.subscription import PlanType
from app.models.user import APIKey, User, UserRole

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


async def resolve_user_from_request(
    request: Request,
    db: AsyncSession,
    credentials: Optional[HTTPAuthorizationCredentials] = None,
    x_api_key: Optional[str] = None,
    required: bool = True,
) -> Optional[User]:
    user: Optional[User] = None
    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get(settings.ACCESS_COOKIE)

    if token:
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            if required:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
            return None
        user_id = payload.get("sub")
        result = await db.execute(
            select(User).options(selectinload(User.subscription)).where(User.id == UUID(user_id))
        )
        user = result.scalar_one_or_none()
    elif x_api_key:
        prefix = x_api_key[:12]
        result = await db.execute(
            select(APIKey)
            .options(selectinload(APIKey.user).selectinload(User.subscription))
            .where(APIKey.key_prefix == prefix, APIKey.is_active.is_(True))
        )
        keys = result.scalars().all()
        for key in keys:
            if verify_api_key(x_api_key, key.key_hash):
                user = key.user
                key.last_used_at = datetime.now(timezone.utc)
                break

    if not user or not user.is_active:
        if required:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        return None
    return user


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await resolve_user_from_request(request, db, credentials, x_api_key, required=True)
    assert user is not None
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Legacy alias — platform admin or super_admin."""
    if user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


def plan_limit(user: User) -> int:
    if user.subscription:
        return user.subscription.generations_limit
    return settings.FREE_GENERATIONS


async def ensure_generation_quota(user: User, db: AsyncSession) -> None:
    """Legacy check — prefer reserve_generation_quota for atomic reserve."""
    from app.services.generation_tracker import ensure_monthly_counters

    ensure_monthly_counters(user)

    limit = plan_limit(user)
    if user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        return
    if user.subscription and user.subscription.plan == PlanType.ENTERPRISE:
        return
    if settings.is_onprem:
        return
    if user.generations_this_month >= limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly generation limit reached ({limit}). Upgrade your plan.",
        )


async def reserve_generation_quota(user: User, db: AsyncSession) -> None:
    """Atomically reserve one generation slot before work starts."""
    from app.services.generation_tracker import ensure_monthly_counters

    ensure_monthly_counters(user)
    await db.flush()

    if user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN) or settings.is_onprem:
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(generations_this_month=User.generations_this_month + 1)
        )
        await db.refresh(user)
        return

    if user.subscription and user.subscription.plan == PlanType.ENTERPRISE:
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(generations_this_month=User.generations_this_month + 1)
        )
        await db.refresh(user)
        return

    limit = plan_limit(user)
    result = await db.execute(
        text(
            """
            UPDATE users
            SET generations_this_month = generations_this_month + 1
            WHERE id = :uid AND generations_this_month < :lim
            RETURNING generations_this_month
            """
        ),
        {"uid": str(user.id), "lim": limit},
    )
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly generation limit reached ({limit}). Upgrade your plan.",
        )
    await db.refresh(user)


async def refund_generation_quota(user: User, db: AsyncSession) -> None:
    await db.execute(
        text(
            """
            UPDATE users
            SET generations_this_month = GREATEST(generations_this_month - 1, 0)
            WHERE id = :uid
            """
        ),
        {"uid": str(user.id)},
    )
    await db.refresh(user)
