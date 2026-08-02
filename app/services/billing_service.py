"""Billing service — Stripe / YuKassa checkout + plan sync."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.subscription import PlanType, Subscription, SubscriptionStatus
from app.models.user import User

settings = get_settings()

PLANS = {
    "free": {
        "id": "free",
        "name": "Free",
        "price_cents": 0,
        "generations": settings.FREE_GENERATIONS,
        "features": ["5 generations / month", "All 7 AI tools", "Community support"],
    },
    "indie": {
        "id": "indie",
        "name": "Indie",
        "price_cents": settings.INDIE_PRICE_CENTS,
        "generations": settings.INDIE_GENERATIONS,
        "features": ["100 generations / month", "Priority queue", "ZIP project export", "Email support"],
    },
    "studio": {
        "id": "studio",
        "name": "Studio",
        "price_cents": settings.STUDIO_PRICE_CENTS,
        "generations": settings.STUDIO_GENERATIONS,
        "features": [
            "1000 generations / month",
            "Team seats (5)",
            "API access",
            "Priority support",
            "Custom style presets",
        ],
    },
    "enterprise": {
        "id": "enterprise",
        "name": "Enterprise",
        "price_cents": 0,
        "generations": 999999,
        "features": ["Unlimited / custom", "On-prem deployment", "SSO", "SLA", "Dedicated success manager"],
    },
}


def list_plans() -> list[dict[str, Any]]:
    return list(PLANS.values())


async def get_or_create_subscription(db: AsyncSession, user: User) -> Subscription:
    result = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = result.scalar_one_or_none()

    # On-prem / forced plan
    forced = settings.FORCE_PLAN or ("enterprise" if settings.is_onprem else "")
    if forced and forced in PLANS:
        if not sub:
            sub = Subscription(
                user_id=user.id,
                plan=PlanType(forced),
                status=SubscriptionStatus.ACTIVE,
                generations_limit=PLANS[forced]["generations"],
                current_period_start=datetime.now(timezone.utc),
                current_period_end=datetime.now(timezone.utc) + timedelta(days=3650),
            )
            db.add(sub)
            await db.flush()
        elif sub.plan.value != forced:
            sub.plan = PlanType(forced)
            sub.generations_limit = PLANS[forced]["generations"]
            await db.flush()
        return sub

    if sub:
        return sub
    sub = Subscription(
        user_id=user.id,
        plan=PlanType.FREE,
        status=SubscriptionStatus.ACTIVE,
        generations_limit=settings.FREE_GENERATIONS,
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(sub)
    await db.flush()
    return sub


async def create_checkout(
    db: AsyncSession,
    user: User,
    plan: str,
    provider: Optional[str] = None,
    success_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
) -> dict[str, Any]:
    if settings.billing_disabled:
        raise ValueError("Billing is disabled in this deployment")

    provider = provider or settings.BILLING_PROVIDER
    success_url = success_url or f"{settings.FRONTEND_URL}/src/pages/dashboard.html?billing=success"
    cancel_url = cancel_url or f"{settings.FRONTEND_URL}/src/pages/dashboard.html?billing=cancel"

    if plan not in ("indie", "studio"):
        raise ValueError("Invalid plan")

    if provider == "stripe" and settings.STRIPE_SECRET_KEY:
        return await _stripe_checkout(user, plan, success_url, cancel_url)

    if provider == "yukassa" and settings.YUKASSA_SHOP_ID and settings.YUKASSA_SECRET_KEY:
        return await _yukassa_checkout(db, user, plan, success_url)

    # Dev mock checkout — instantly upgrades
    await apply_plan(db, user, plan)
    return {
        "checkout_url": f"{success_url}&mock=1&plan={plan}",
        "session_id": f"mock_{plan}_{user.id}",
        "mock": True,
    }


async def apply_plan(db: AsyncSession, user: User, plan: str) -> Subscription:
    sub = await get_or_create_subscription(db, user)
    # Avoid on-prem forced plan override fighting apply during saas mock
    if settings.is_onprem and settings.FORCE_PLAN:
        return sub
    plan_enum = PlanType(plan)
    sub.plan = plan_enum
    sub.status = SubscriptionStatus.ACTIVE
    sub.generations_limit = PLANS[plan]["generations"]
    sub.current_period_start = datetime.now(timezone.utc)
    sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
    await db.flush()

    # Auto-create org shell for Studio so seats are ready
    if plan == "studio":
        from app.models.organization import OrgMemberRole, OrgMembership, Organization

        existing = await db.execute(select(OrgMembership).where(OrgMembership.user_id == user.id).limit(1))
        if not existing.scalar_one_or_none():
            org = Organization(
                name=f"{user.full_name or user.email.split('@')[0]} Studio",
                owner_id=user.id,
                seats_limit=settings.STUDIO_SEATS,
            )
            db.add(org)
            await db.flush()
            db.add(OrgMembership(organization_id=org.id, user_id=user.id, role=OrgMemberRole.OWNER))
            await db.flush()
    return sub


async def _stripe_checkout(user: User, plan: str, success_url: str, cancel_url: str) -> dict[str, Any]:
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    price = settings.STRIPE_PRICE_INDIE if plan == "indie" else settings.STRIPE_PRICE_STUDIO
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        customer_email=user.email,
        metadata={"user_id": str(user.id), "plan": plan},
    )
    return {"checkout_url": session.url, "session_id": session.id}


async def _yukassa_checkout(
    db: AsyncSession, user: User, plan: str, success_url: str
) -> dict[str, Any]:
    import uuid

    import httpx

    amount = PLANS[plan]["price_cents"] / 100
    idempotence = str(uuid.uuid4())
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.yookassa.ru/v3/payments",
            auth=(settings.YUKASSA_SHOP_ID, settings.YUKASSA_SECRET_KEY),
            headers={"Idempotence-Key": idempotence},
            json={
                "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
                "confirmation": {"type": "redirect", "return_url": success_url},
                "capture": True,
                "description": f"AI Game Dev Toolkit — {plan}",
                "metadata": {"user_id": str(user.id), "plan": plan},
            },
        )
        resp.raise_for_status()
        data = resp.json()
    sub = await get_or_create_subscription(db, user)
    sub.yukassa_payment_id = data.get("id")
    await db.flush()
    return {
        "checkout_url": data["confirmation"]["confirmation_url"],
        "session_id": data.get("id"),
    }


async def handle_stripe_webhook(db: AsyncSession, payload: bytes, sig_header: str) -> None:
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")
        plan = session.get("metadata", {}).get("plan", "indie")
        if user_id:
            result = await db.execute(select(User).where(User.id == UUID(user_id)))
            user = result.scalar_one_or_none()
            if user:
                sub = await apply_plan(db, user, plan)
                sub.stripe_customer_id = session.get("customer")
                sub.stripe_subscription_id = session.get("subscription")
