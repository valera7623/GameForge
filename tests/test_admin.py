"""Admin panel API tests — RBAC, users, tools, dashboard."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import hash_password
from app.models.subscription import PlanType, Subscription, SubscriptionStatus
from app.models.user import User, UserRole

settings = get_settings()


async def _make_user(
    db: AsyncSession,
    email: str,
    role: UserRole,
    *,
    password: str = "password12345",
    plan: PlanType = PlanType.FREE,
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=email.split("@")[0],
        role=role,
        is_verified=True,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    db.add(
        Subscription(
            user_id=user.id,
            plan=plan,
            status=SubscriptionStatus.ACTIVE,
            generations_limit=settings.FREE_GENERATIONS if plan == PlanType.FREE else settings.INDIE_GENERATIONS,
        )
    )
    await db.commit()
    await db.refresh(user)
    return user


async def _login(client: AsyncClient, email: str, password: str = "password12345") -> None:
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text


@pytest.mark.asyncio
async def test_admin_me_and_dashboard(client: AsyncClient, db_session: AsyncSession):
    await _make_user(db_session, "super@test.ai", UserRole.SUPER_ADMIN)
    await _login(client, "super@test.ai")

    me = await client.get("/api/v1/admin/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["role"] == "super_admin"
    assert "settings:write" in body["permissions"]

    dash = await client.get("/api/v1/admin/dashboard")
    assert dash.status_code == 200
    assert "users_total" in dash.json()


@pytest.mark.asyncio
async def test_support_cannot_block_or_toggle(client: AsyncClient, db_session: AsyncSession):
    await _make_user(db_session, "support@test.ai", UserRole.SUPPORT)
    target = await _make_user(db_session, "victim@test.ai", UserRole.USER)
    await _login(client, "support@test.ai")

    users = await client.get("/api/v1/admin/users")
    assert users.status_code == 200

    blocked = await client.post(f"/api/v1/admin/users/{target.id}/block")
    assert blocked.status_code == 403

    tools = await client.get("/api/v1/admin/tools")
    assert tools.status_code == 200
    name = tools.json()["tools"][0]["name"]
    toggle = await client.post(f"/api/v1/admin/tools/{name}/toggle")
    assert toggle.status_code == 403


@pytest.mark.asyncio
async def test_admin_block_and_tool_toggle(client: AsyncClient, db_session: AsyncSession):
    await _make_user(db_session, "admin@test.ai", UserRole.ADMIN)
    target = await _make_user(db_session, "user2@test.ai", UserRole.USER)
    await _login(client, "admin@test.ai")

    blocked = await client.post(f"/api/v1/admin/users/{target.id}/block")
    assert blocked.status_code == 200
    assert blocked.json()["is_active"] is False

    settings_put = await client.put("/api/v1/admin/settings", json={"app_name": "X"})
    assert settings_put.status_code == 403

    tools = await client.get("/api/v1/admin/tools")
    name = tools.json()["tools"][0]["name"]
    before = tools.json()["tools"][0]["enabled"]
    toggled = await client.post(f"/api/v1/admin/tools/{name}/toggle")
    assert toggled.status_code == 200
    assert toggled.json()["enabled"] is (not before)


@pytest.mark.asyncio
async def test_regular_user_forbidden(client: AsyncClient, db_session: AsyncSession):
    await _make_user(db_session, "normal@test.ai", UserRole.USER)
    await _login(client, "normal@test.ai")
    res = await client.get("/api/v1/admin/dashboard")
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_admin_cannot_assign_super_admin(client: AsyncClient, db_session: AsyncSession):
    await _make_user(db_session, "admin2@test.ai", UserRole.ADMIN)
    target = await _make_user(db_session, "user3@test.ai", UserRole.USER)
    await _login(client, "admin2@test.ai")
    res = await client.post(
        f"/api/v1/admin/users/{target.id}/role",
        json={"role": "super_admin"},
    )
    assert res.status_code == 403
