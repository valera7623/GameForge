"""FastAPI dependencies: auth, DB, generation quota."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.security import decode_token, verify_api_key
from app.database import get_db
from app.models.subscription import PlanType, Subscription
from app.models.user import APIKey, User, UserRole

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> User:
    user: Optional[User] = None

    if credentials and credentials.credentials:
        payload = decode_token(credentials.credentials)
        if not payload or payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        user_id = payload.get("sub")
        result = await db.execute(
            select(User).options(selectinload(User.subscription)).where(User.id == UUID(user_id))
        )
        user = result.scalar_one_or_none()
    elif x_api_key:
        # Look up by prefix then verify hash
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


def plan_limit(user: User) -> int:
    if user.subscription:
        return user.subscription.generations_limit
    return settings.FREE_GENERATIONS


async def ensure_generation_quota(user: User, db: AsyncSession) -> None:
    """Reset monthly counter if needed and check quota."""
    from app.services.generation_tracker import ensure_monthly_counters

    ensure_monthly_counters(user)

    limit = plan_limit(user)
    if user.role == UserRole.ADMIN:
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
