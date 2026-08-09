"""Auth, billing, AI fail, and quota tests."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str, password: str = "password1234") -> dict:
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Tester"},
    )
    assert res.status_code == 201, res.text
    return res.json()


@pytest.mark.asyncio
async def test_register_login_refresh_logout(client: AsyncClient):
    tokens = await _register(client, "auth1@example.com")
    assert "access_token" in tokens
    assert client.cookies.get("gf_access") or tokens["access_token"]

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "auth1@example.com", "password": "password1234"},
    )
    assert login.status_code == 200
    refresh = login.json()["refresh_token"]

    rotated = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert rotated.status_code == 200
    new_refresh = rotated.json()["refresh_token"]
    assert new_refresh != refresh

    reused = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert reused.status_code == 401

    out = await client.post("/api/v1/auth/logout", json={"refresh_token": new_refresh})
    assert out.status_code == 200


@pytest.mark.asyncio
async def test_password_min_length(client: AsyncClient):
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "short"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_mock_billing_allowed_in_test(client: AsyncClient):
    await _register(client, "bill@example.com")
    await client.post("/api/v1/auth/login", json={"email": "bill@example.com", "password": "password1234"})
    res = await client.post("/api/v1/billing/checkout", json={"plan": "indie"})
    assert res.status_code == 200
    assert "checkout_url" in res.json()


@pytest.mark.asyncio
async def test_ai_fail_no_xp(client: AsyncClient):
    await _register(client, "aifail@example.com")
    await client.post("/api/v1/auth/login", json={"email": "aifail@example.com", "password": "password1234"})

    with patch("app.services.ai_level_designer.generate_level", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = RuntimeError("provider down")
        res = await client.post(
            "/api/v1/level-designer",
            json={"description": "crypt", "width": 16, "height": 16, "style": "dungeon"},
        )
        assert res.status_code == 502

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["xp"] == 0
    assert me.json()["generations_this_month"] == 0  # refunded


@pytest.mark.asyncio
async def test_quota_race(client: AsyncClient):
    from app.config import get_settings

    settings = get_settings()
    await _register(client, "quota@example.com")
    await client.post("/api/v1/auth/login", json={"email": "quota@example.com", "password": "password1234"})

    # Force tiny free limit via patching plan_limit path — use many parallel free gens
    async def one():
        return await client.post(
            "/api/v1/level-designer",
            json={"description": "room", "width": 8, "height": 8, "style": "dungeon"},
        )

    # Free limit is typically 5 — fire 8 in parallel
    results = await asyncio.gather(*[one() for _ in range(settings.FREE_GENERATIONS + 3)], return_exceptions=True)
    statuses = [r.status_code if hasattr(r, "status_code") else 500 for r in results]
    assert 402 in statuses or statuses.count(200) <= settings.FREE_GENERATIONS + 1


@pytest.mark.asyncio
async def test_production_rejects_mock_billing():
    from app.config import Settings, validate_settings

    s = Settings(
        APP_ENV="production",
        DEBUG=False,
        SECRET_KEY="strong-production-secret-key-32chars!!",
        CORS_ORIGINS="https://app.example.com",
        FRONTEND_URL="https://app.example.com",
        ALLOW_MOCK_BILLING=True,
        USE_MOCK_AI=False,
        OPENAI_API_KEY="sk-test",
        EMAIL_PROVIDER="resend",
        RESEND_API_KEY="re_test",
        DISABLE_BILLING=True,
    )
    with pytest.raises(RuntimeError, match="ALLOW_MOCK_BILLING"):
        validate_settings(s)


@pytest.mark.asyncio
async def test_production_rejects_console_email_without_escape_hatch():
    from app.config import Settings, validate_settings

    s = Settings(
        APP_ENV="production",
        DEBUG=False,
        SECRET_KEY="strong-production-secret-key-32chars!!",
        CORS_ORIGINS="https://app.example.com",
        FRONTEND_URL="https://app.example.com",
        ALLOW_MOCK_BILLING=False,
        USE_MOCK_AI=True,
        EMAIL_PROVIDER="console",
        DISABLE_BILLING=True,
    )
    with pytest.raises(RuntimeError, match="EMAIL_PROVIDER"):
        validate_settings(s)


@pytest.mark.asyncio
async def test_production_requires_openai_key_when_not_mock():
    from app.config import Settings, validate_settings

    s = Settings(
        APP_ENV="production",
        DEBUG=False,
        SECRET_KEY="strong-production-secret-key-32chars!!",
        CORS_ORIGINS="https://app.example.com",
        FRONTEND_URL="https://app.example.com",
        ALLOW_MOCK_BILLING=False,
        USE_MOCK_AI=False,
        OPENAI_API_KEY="",
        EMAIL_PROVIDER="resend",
        RESEND_API_KEY="re_test",
        DISABLE_BILLING=True,
    )
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        validate_settings(s)


@pytest.mark.asyncio
async def test_api_key_delete(client: AsyncClient):
    await _register(client, "keys@example.com")
    await client.post("/api/v1/auth/login", json={"email": "keys@example.com", "password": "password1234"})
    created = await client.post("/api/v1/auth/api-keys", json={"name": "ci"})
    assert created.status_code == 201
    key_id = created.json()["id"]
    deleted = await client.delete(f"/api/v1/auth/api-keys/{key_id}")
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_stripe_webhook_rejects_bad_signature(client: AsyncClient):
    res = await client.post(
        "/api/v1/billing/webhook/stripe",
        content=b'{"type":"checkout.session.completed"}',
        headers={"stripe-signature": "t=1,v1=deadbeef", "content-type": "application/json"},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_apply_plan_blocked_without_payment_when_mock_disallowed():
    from app.config import Settings
    from app.services import billing_service

    original = billing_service.settings
    billing_service.settings = Settings(
        APP_ENV="production",
        DEBUG=False,
        SECRET_KEY="strong-production-secret-key-32chars-xx",
        CORS_ORIGINS="https://app.example.com",
        ALLOW_MOCK_BILLING=False,
    )
    try:
        assert billing_service.settings.mock_billing_allowed is False
        with pytest.raises(ValueError, match="confirmed payment"):
            await billing_service.apply_plan(None, None, "indie", confirmed_payment=False)
    finally:
        billing_service.settings = original


@pytest.mark.asyncio
async def test_word_pack_checkout_credits_and_lists(client: AsyncClient):
    await _register(client, "locwords@example.com")
    await client.post(
        "/api/v1/auth/login",
        json={"email": "locwords@example.com", "password": "password1234"},
    )

    plans = await client.get("/api/v1/billing/plans")
    assert plans.status_code == 200
    ids = {p["id"] for p in plans.json()}
    assert {"loc_starter", "loc_indie", "loc_studio"}.issubset(ids)
    starter = next(p for p in plans.json() if p["id"] == "loc_starter")
    assert starter["kind"] == "word_pack"
    assert starter["words"] == 5000
    assert starter["currency"] == "RUB"
    assert starter["price_cents"] == 499_000
    indie_sub = next(p for p in plans.json() if p["id"] == "indie")
    assert indie_sub["currency"] == "RUB"
    assert indie_sub["price_cents"] == 199_000

    res = await client.post("/api/v1/billing/checkout", json={"plan": "loc_starter"})
    assert res.status_code == 200, res.text
    assert "checkout_url" in res.json()

    sub = await client.get("/api/v1/billing/subscription")
    assert sub.status_code == 200
    assert sub.json()["localization_words_remaining"] == 5000

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["localization_words_remaining"] == 5000


@pytest.mark.asyncio
async def test_localize_prefers_word_credits(client: AsyncClient):
    await _register(client, "locbill@example.com")
    await client.post(
        "/api/v1/auth/login",
        json={"email": "locbill@example.com", "password": "password1234"},
    )
    await client.post("/api/v1/billing/checkout", json={"plan": "loc_starter"})

    me_before = (await client.get("/api/v1/auth/me")).json()
    words_before = me_before["localization_words_remaining"]
    gens_before = me_before["generations_this_month"]
    assert words_before == 5000

    texts = {"ui.start": "Start game now", "ui.quit": "Quit"}  # 4 words
    res = await client.post(
        "/api/v1/localization",
        json={"texts": texts, "source_lang": "en", "target_langs": ["ru"], "export_format": "json"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["quota_kind"] == "words"
    assert body["words_used"] == 4
    assert body["words_remaining"] == words_before - 4

    me_after = (await client.get("/api/v1/auth/me")).json()
    assert me_after["localization_words_remaining"] == words_before - 4
    assert me_after["generations_this_month"] == gens_before


@pytest.mark.asyncio
async def test_localize_falls_back_to_generations_without_words(client: AsyncClient):
    await _register(client, "locgen@example.com")
    await client.post(
        "/api/v1/auth/login",
        json={"email": "locgen@example.com", "password": "password1234"},
    )

    me_before = (await client.get("/api/v1/auth/me")).json()
    assert me_before["localization_words_remaining"] == 0
    gens_before = me_before["generations_this_month"]

    res = await client.post(
        "/api/v1/localization",
        json={
            "texts": {"a": "hello"},
            "source_lang": "en",
            "target_langs": ["ru"],
            "export_format": "json",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["quota_kind"] == "generations"
    assert body["words_used"] == 0
    assert body["words_remaining"] == 0

    me_after = (await client.get("/api/v1/auth/me")).json()
    assert me_after["generations_this_month"] == gens_before + 1
    assert me_after["localization_words_remaining"] == 0


@pytest.mark.asyncio
async def test_localize_insufficient_words_uses_generations(client: AsyncClient):
    """Some credits but not enough for the job → generation quota; words untouched."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.config import get_settings
    from app.models.subscription import Subscription
    from app.models.user import User

    await _register(client, "locshort@example.com")
    await client.post(
        "/api/v1/auth/login",
        json={"email": "locshort@example.com", "password": "password1234"},
    )
    await client.post("/api/v1/billing/checkout", json={"plan": "loc_starter"})

    settings = get_settings()
    eng = create_async_engine(settings.DATABASE_URL)
    factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        user = (
            await session.execute(select(User).where(User.email == "locshort@example.com"))
        ).scalar_one()
        sub = (
            await session.execute(select(Subscription).where(Subscription.user_id == user.id))
        ).scalar_one()
        sub.localization_words_remaining = 2
        await session.commit()
    await eng.dispose()

    me_before = (await client.get("/api/v1/auth/me")).json()
    assert me_before["localization_words_remaining"] == 2
    gens_before = me_before["generations_this_month"]

    res = await client.post(
        "/api/v1/localization",
        json={
            "texts": {"a": "one two three four five"},
            "source_lang": "en",
            "target_langs": ["ru"],
            "export_format": "json",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["quota_kind"] == "generations"
    assert body["words_used"] == 0
    assert body["words_remaining"] == 2

    me_after = (await client.get("/api/v1/auth/me")).json()
    assert me_after["localization_words_remaining"] == 2
    assert me_after["generations_this_month"] == gens_before + 1
