"""Dashboard usage reset."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import hash_password
from app.models.subscription import PlanType, Subscription, SubscriptionStatus
from app.models.user import User, UserRole
from app.services.generation_tracker import current_month_key

settings = get_settings()


async def _make_user(
    db: AsyncSession,
    email: str,
    *,
    role: UserRole = UserRole.USER,
    plan: PlanType = PlanType.FREE,
    gens_month: int = 12,
    total_gens: int = 20,
    xp_month: int = 100,
) -> User:
    now = datetime.now(timezone.utc)
    user = User(
        email=email,
        hashed_password=hash_password("password12345"),
        full_name=email.split("@")[0],
        role=role,
        is_verified=True,
        is_active=True,
        generations_this_month=gens_month,
        generation_reset_at=now,
        total_generations=total_gens,
        xp_this_month=xp_month,
        xp_month_key=current_month_key(now),
        xp=xp_month,
    )
    db.add(user)
    await db.flush()
    limit = {
        PlanType.FREE: settings.FREE_GENERATIONS,
        PlanType.INDIE: settings.INDIE_GENERATIONS,
        PlanType.STUDIO: settings.STUDIO_GENERATIONS,
        PlanType.ENTERPRISE: 999_999,
    }[plan]
    db.add(
        Subscription(
            user_id=user.id,
            plan=plan,
            status=SubscriptionStatus.ACTIVE,
            generations_limit=limit,
        )
    )
    await db.commit()
    await db.refresh(user)
    return user


async def _login(client: AsyncClient, email: str) -> None:
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": "password12345"})
    assert res.status_code == 200, res.text


@pytest.mark.asyncio
async def test_reset_usage_zeros_counters(client: AsyncClient, db_session: AsyncSession):
    await _make_user(db_session, "reset-ent@test.ai", plan=PlanType.ENTERPRISE)
    await _login(client, "reset-ent@test.ai")

    before = await client.get("/api/v1/dashboard")
    assert before.status_code == 200
    assert before.json()["can_reset_usage"] is True
    assert before.json()["generations_this_month"] == 12

    reset = await client.post("/api/v1/dashboard/reset-usage")
    assert reset.status_code == 200, reset.text
    body = reset.json()
    assert body["generations_this_month"] == 0
    assert body["total_generations"] == 0
    assert body["xp_this_month"] == 0
    assert body["xp"] == 100  # lifetime XP kept
    assert body["projects_count"] == 0
