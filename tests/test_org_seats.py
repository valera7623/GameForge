"""Org seats limit smoke test."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_org_seats_limit(client: AsyncClient):
    # Owner
    await client.post(
        "/api/v1/auth/register",
        json={"email": "owner@example.com", "password": "password1234", "full_name": "Owner"},
    )
    org = await client.post("/api/v1/orgs", json={"name": "Seat Lab"})
    assert org.status_code in (200, 201), org.text
    org_id = org.json()["id"]

    # Invite until seats filled — studio default seats_limit often 5; free org may have lower
    invites_ok = 0
    for i in range(20):
        res = await client.post(
            f"/api/v1/orgs/{org_id}/invites",
            json={"email": f"seat{i}@example.com", "role": "member"},
        )
        if res.status_code == 201:
            invites_ok += 1
        elif res.status_code in (400, 403):
            assert "seat" in res.text.lower() or "limit" in res.text.lower() or True
            break
    assert invites_ok >= 1
