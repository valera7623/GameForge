"""Signup attribution (LocForge / UTM)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


@pytest.mark.asyncio
async def test_register_stores_locforge_attribution(client: AsyncClient, db_session: AsyncSession):
    email = "locforge-attr@example.com"
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "password12345",
            "full_name": "Loc Pilot",
            "signup_source": "locforge",
            "signup_pack": "starter",
            "attribution": {
                "utm_source": "discord",
                "utm_medium": "dm",
                "utm_campaign": "lf_en",
                "from": "locforge",
                "pack": "starter",
            },
        },
    )
    assert res.status_code == 201, res.text

    row = (
        await db_session.execute(select(User).where(User.email == email))
    ).scalar_one()
    assert row.signup_source == "locforge"
    assert row.signup_pack == "starter"
    assert row.attribution["utm_source"] == "discord"
    assert row.first_localize_notified is False

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["signup_source"] == "locforge"
    assert body["signup_pack"] == "starter"
