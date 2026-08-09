"""Feedback form API tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import hash_password
from app.models.subscription import PlanType, Subscription, SubscriptionStatus
from app.models.user import User, UserRole

settings = get_settings()


async def _make_staff(db: AsyncSession, email: str = "admin-fb@test.ai") -> User:
    user = User(
        email=email,
        hashed_password=hash_password("password12345"),
        full_name="Admin",
        role=UserRole.ADMIN,
        is_verified=True,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    db.add(
        Subscription(
            user_id=user.id,
            plan=PlanType.FREE,
            status=SubscriptionStatus.ACTIVE,
            generations_limit=settings.FREE_GENERATIONS,
        )
    )
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_submit_feedback_requires_consent(client: AsyncClient):
    res = await client.post(
        "/api/v1/feedback",
        json={
            "category": "bug",
            "email": "user@example.com",
            "message": "Something is broken in the texture tool.",
            "consent": False,
        },
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_submit_feedback_ok(client: AsyncClient):
    with patch("app.api.v1.feedback.send_email", new_callable=AsyncMock) as mocked:
        mocked.return_value = True
        res = await client.post(
            "/api/v1/feedback",
            json={
                "category": "idea",
                "email": "user@example.com",
                "subject": "Dark mode for admin",
                "message": "Please add dark mode everywhere in the admin panel.",
                "consent": True,
                "page_url": "https://gameforge.website/feedback",
            },
        )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["ok"] is True
    assert body["id"]
    mocked.assert_awaited()


@pytest.mark.asyncio
async def test_honeypot_silent_success(client: AsyncClient):
    with patch("app.api.v1.feedback.send_email", new_callable=AsyncMock) as mocked:
        res = await client.post(
            "/api/v1/feedback",
            json={
                "category": "other",
                "email": "bot@example.com",
                "message": "This is spam from a bot filling the honeypot.",
                "consent": True,
                "website": "http://spam.example",
            },
        )
    assert res.status_code == 201
    mocked.assert_not_called()


@pytest.mark.asyncio
async def test_admin_feedback_list_and_patch(client: AsyncClient, db_session: AsyncSession):
    await _make_staff(db_session)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin-fb@test.ai", "password": "password12345"},
    )
    assert login.status_code == 200, login.text

    with patch("app.api.v1.feedback.send_email", new_callable=AsyncMock, return_value=True):
        created = await client.post(
            "/api/v1/feedback",
            json={
                "category": "billing",
                "email": "payer@example.com",
                "message": "I was charged twice for the indie plan this month.",
                "consent": True,
            },
        )
    assert created.status_code == 201
    fid = created.json()["id"]

    listed = await client.get("/api/v1/admin/feedback")
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert any(i["id"] == fid for i in items)

    patched = await client.patch(
        f"/api/v1/admin/feedback/{fid}",
        json={"status": "read", "admin_note": "Looking into YuKassa"},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "read"
    assert patched.json()["admin_note"] == "Looking into YuKassa"
