"""Admin upgrade tests — AI models, content CMS, logs purge, costing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ops_log import AuditLog, ErrorLog
from app.models.user import UserRole
from app.services.ai_costing import estimate_cost_usd
from app.services.markdown_html import md_to_html
from app.services.openai_client import LlmUsage
from app.services.ops_logs import purge_ops_logs
from tests.test_admin import _login, _make_user


def test_md_to_html_basic():
    html = md_to_html("# Hello\n\n**bold** and `code`\n\n- a\n- b")
    assert "<h1>" in html
    assert "<strong>bold</strong>" in html
    assert "<code>code</code>" in html
    assert "<ul>" in html


def test_estimate_cost_chat():
    usage = LlmUsage(prompt_tokens=1_000_000, completion_tokens=500_000, cost_key="openai_chat")
    cost = estimate_cost_usd(usage)
    # 0.15 + 0.30 = 0.45 with defaults
    assert cost == Decimal("0.450000")


@pytest.mark.asyncio
async def test_ai_models_rbac(client: AsyncClient, db_session: AsyncSession):
    await _make_user(db_session, "admin-ai@test.ai", UserRole.ADMIN)
    await _login(client, "admin-ai@test.ai")
    get = await client.get("/api/v1/admin/ai-models")
    assert get.status_code == 200
    put = await client.put("/api/v1/admin/ai-models", json={"models": {"openai_chat": {"input_per_1m": 1}}})
    assert put.status_code == 403

    await _make_user(db_session, "super-ai@test.ai", UserRole.SUPER_ADMIN)
    await _login(client, "super-ai@test.ai")
    put2 = await client.put(
        "/api/v1/admin/ai-models",
        json={"models": {"openai_chat": {"model": "gpt-test", "input_per_1m": 1.0, "output_per_1m": 2.0}}},
    )
    assert put2.status_code == 200
    costs = await client.get("/api/v1/admin/ai-models/costs?days=7")
    assert costs.status_code == 200
    assert "total_usd" in costs.json()


@pytest.mark.asyncio
async def test_block_creates_audit(client: AsyncClient, db_session: AsyncSession):
    await _make_user(db_session, "admin-aud@test.ai", UserRole.ADMIN)
    target = await _make_user(db_session, "victim-aud@test.ai", UserRole.USER)
    await _login(client, "admin-aud@test.ai")
    res = await client.post(f"/api/v1/admin/users/{target.id}/block")
    assert res.status_code == 200
    logs = await client.get("/api/v1/admin/logs/audit")
    assert logs.status_code == 200
    actions = [i["action"] for i in logs.json()["items"]]
    assert "user.block" in actions


@pytest.mark.asyncio
async def test_content_publish_and_public(client: AsyncClient, db_session: AsyncSession):
    await _make_user(db_session, "mgr@test.ai", UserRole.MANAGER)
    await _login(client, "mgr@test.ai")
    created = await client.post(
        "/api/v1/admin/content",
        json={
            "kind": "faq",
            "slug": "what-is-gf",
            "locale": "en",
            "title": "What is GameForge?",
            "body_md": "## Answer\n\nAn AI toolkit.",
        },
    )
    assert created.status_code == 200, created.text
    item_id = created.json()["id"]

    public_before = await client.get("/api/v1/content/faq?locale=en")
    assert public_before.status_code == 200
    assert all(i["id"] != item_id for i in public_before.json()["items"])

    pub = await client.post(f"/api/v1/admin/content/{item_id}/publish")
    assert pub.status_code == 200
    assert pub.json()["status"] == "published"

    public_after = await client.get("/api/v1/content/faq?locale=en")
    assert any(i["id"] == item_id for i in public_after.json()["items"])

    await _make_user(db_session, "sup-c@test.ai", UserRole.SUPPORT)
    await _login(client, "sup-c@test.ai")
    deny = await client.post(f"/api/v1/admin/content/{item_id}/unpublish")
    assert deny.status_code == 403


@pytest.mark.asyncio
async def test_purge_ops_logs_cutoff(client: AsyncClient, db_session: AsyncSession):
    old = AuditLog(
        action="old.action",
        created_at=datetime.now(timezone.utc) - timedelta(days=45),
    )
    recent = AuditLog(action="new.action")
    err = ErrorLog(
        source="api",
        message="old error",
        created_at=datetime.now(timezone.utc) - timedelta(days=40),
    )
    db_session.add_all([old, recent, err])
    await db_session.commit()

    deleted = await purge_ops_logs(db_session, days=30)
    await db_session.commit()
    assert deleted["audit"] >= 1
    assert deleted["errors"] >= 1

    await _make_user(db_session, "super-purge@test.ai", UserRole.SUPER_ADMIN)
    await _login(client, "super-purge@test.ai")
    logs = await client.get("/api/v1/admin/logs/audit")
    assert logs.status_code == 200
    actions = [i["action"] for i in logs.json()["items"]]
    assert "old.action" not in actions
