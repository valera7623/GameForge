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
        "words": None,
        "kind": "subscription",
        "features": ["5 generations / month", "All 7 AI tools", "Community support"],
    },
    "indie": {
        "id": "indie",
        "name": "Indie",
        "price_cents": settings.INDIE_PRICE_CENTS,
        "generations": settings.INDIE_GENERATIONS,
        "words": None,
        "kind": "subscription",
        "features": ["100 generations / month", "Priority queue", "ZIP project export", "Email support"],
    },
    "studio": {
        "id": "studio",
        "name": "Studio",
        "price_cents": settings.STUDIO_PRICE_CENTS,
        "generations": settings.STUDIO_GENERATIONS,
        "words": None,
        "kind": "subscription",
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
        "words": None,
        "kind": "subscription",
        "features": ["Unlimited / custom", "On-prem deployment", "SSO", "SLA", "Dedicated success manager"],
    },
}

WORD_PACKS = {
    "loc_starter": {
        "id": "loc_starter",
        "name": "LocForge Starter",
        "price_cents": settings.LOC_STARTER_PRICE_CENTS,
        "generations": 0,
        "words": settings.LOC_STARTER_WORDS,
        "kind": "word_pack",
        "features": [f"{settings.LOC_STARTER_WORDS:,} localization words", "CSV + glossary + length QA"],
    },
    "loc_indie": {
        "id": "loc_indie",
        "name": "LocForge Indie",
        "price_cents": settings.LOC_INDIE_PRICE_CENTS,
        "generations": 0,
        "words": settings.LOC_INDIE_WORDS,
        "kind": "word_pack",
        "features": [f"{settings.LOC_INDIE_WORDS:,} localization words", "CSV + glossary + length QA"],
    },
    "loc_studio": {
        "id": "loc_studio",
        "name": "LocForge Studio",
        "price_cents": settings.LOC_STUDIO_PRICE_CENTS,
        "generations": 0,
        "words": settings.LOC_STUDIO_WORDS,
        "kind": "word_pack",
        "features": [f"{settings.LOC_STUDIO_WORDS:,} localization words", "CSV + glossary + length QA", "Unity / Godot export"],
    },
}

SUBSCRIPTION_CHECKOUT_PLANS = frozenset({"indie", "studio"})
WORD_PACK_IDS = frozenset(WORD_PACKS.keys())
CHECKOUT_PLANS = SUBSCRIPTION_CHECKOUT_PLANS | WORD_PACK_IDS


def list_plans() -> list[dict[str, Any]]:
    return [*PLANS.values(), *WORD_PACKS.values()]


def is_word_pack(plan: str) -> bool:
    return plan in WORD_PACK_IDS


async def get_or_create_subscription(db: AsyncSession, user: User) -> Subscription:
    result = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = result.scalar_one_or_none()

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
    success_url = success_url or f"{settings.FRONTEND_URL}/dashboard?billing=success"
    cancel_url = cancel_url or f"{settings.FRONTEND_URL}/dashboard?billing=cancel"

    if plan not in CHECKOUT_PLANS:
        raise ValueError("Invalid plan")

    if provider == "stripe" and settings.STRIPE_SECRET_KEY:
        if is_word_pack(plan):
            return await _stripe_word_pack_checkout(user, plan, success_url, cancel_url)
        return await _stripe_checkout(user, plan, success_url, cancel_url)

    if provider == "yukassa" and settings.YUKASSA_SHOP_ID and settings.YUKASSA_SECRET_KEY:
        return await _yukassa_checkout(db, user, plan, success_url)

    if not settings.mock_billing_allowed:
        raise ValueError(
            "Payment provider is not configured. Set Stripe or YuKassa credentials."
        )

    if is_word_pack(plan):
        await apply_word_pack(db, user, plan, confirmed_payment=True)
    else:
        await apply_plan(db, user, plan, confirmed_payment=True)
    return {
        "checkout_url": f"{success_url}&mock=1&plan={plan}",
        "session_id": f"mock_{plan}_{user.id}",
        "mock": True,
    }


async def apply_word_pack(
    db: AsyncSession,
    user: User,
    plan: str,
    *,
    confirmed_payment: bool = False,
) -> Subscription:
    if plan not in WORD_PACKS:
        raise ValueError("Invalid word pack")
    if not confirmed_payment and not settings.mock_billing_allowed:
        raise ValueError("Word pack purchases require a confirmed payment in this environment")

    sub = await get_or_create_subscription(db, user)
    if settings.is_onprem and settings.FORCE_PLAN:
        return sub
    words = int(WORD_PACKS[plan]["words"] or 0)
    sub.localization_words_remaining = int(sub.localization_words_remaining or 0) + words
    await db.flush()
    return sub


async def apply_plan(
    db: AsyncSession,
    user: User,
    plan: str,
    *,
    confirmed_payment: bool = False,
) -> Subscription:
    if is_word_pack(plan):
        return await apply_word_pack(db, user, plan, confirmed_payment=confirmed_payment)

    if not confirmed_payment and not settings.mock_billing_allowed:
        raise ValueError("Plan changes require a confirmed payment in this environment")

    sub = await get_or_create_subscription(db, user)
    if settings.is_onprem and settings.FORCE_PLAN:
        return sub
    plan_enum = PlanType(plan)
    sub.plan = plan_enum
    sub.status = SubscriptionStatus.ACTIVE
    sub.generations_limit = PLANS[plan]["generations"]
    sub.current_period_start = datetime.now(timezone.utc)
    sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
    await db.flush()

    if plan == "studio":
        from app.models.organization import Organization, OrgMemberRole, OrgMembership

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


async def downgrade_to_free(db: AsyncSession, user: User) -> Subscription:
    sub = await get_or_create_subscription(db, user)
    sub.plan = PlanType.FREE
    sub.status = SubscriptionStatus.CANCELED
    sub.generations_limit = settings.FREE_GENERATIONS
    await db.flush()
    return sub


async def create_billing_portal(user: User, return_url: Optional[str] = None) -> dict[str, Any]:
    if not settings.STRIPE_SECRET_KEY:
        raise ValueError("Stripe is not configured")
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    return_url = return_url or settings.STRIPE_PORTAL_RETURN_URL or f"{settings.FRONTEND_URL}/dashboard"
    # Need customer id — look up from subscription via sync caller
    raise ValueError("Use create_customer_portal with subscription context")


async def create_customer_portal(db: AsyncSession, user: User, return_url: Optional[str] = None) -> dict[str, str]:
    import stripe

    if not settings.STRIPE_SECRET_KEY:
        raise ValueError("Stripe is not configured")
    sub = await get_or_create_subscription(db, user)
    if not sub.stripe_customer_id:
        raise ValueError("No Stripe customer on this account")
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return_url = return_url or settings.STRIPE_PORTAL_RETURN_URL or f"{settings.FRONTEND_URL}/dashboard"
    session = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url=return_url,
    )
    return {"portal_url": session.url}


async def cancel_subscription(db: AsyncSession, user: User) -> Subscription:
    import stripe

    sub = await get_or_create_subscription(db, user)
    if sub.stripe_subscription_id and settings.STRIPE_SECRET_KEY:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        stripe.Subscription.modify(sub.stripe_subscription_id, cancel_at_period_end=True)
        sub.status = SubscriptionStatus.CANCELED
        await db.flush()
        return sub
    if settings.mock_billing_allowed:
        return await downgrade_to_free(db, user)
    raise ValueError("Cannot cancel: no active Stripe subscription")


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


async def _stripe_word_pack_checkout(
    user: User, plan: str, success_url: str, cancel_url: str
) -> dict[str, Any]:
    import stripe

    pack = WORD_PACKS[plan]
    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": pack["price_cents"],
                    "product_data": {
                        "name": pack["name"],
                        "description": f"{pack['words']} localization words",
                    },
                },
                "quantity": 1,
            }
        ],
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

    catalog = WORD_PACKS if is_word_pack(plan) else PLANS
    amount = catalog[plan]["price_cents"] / 100
    description = (
        f"LocForge — {catalog[plan]['name']}"
        if is_word_pack(plan)
        else f"AI Game Dev Toolkit — {plan}"
    )
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
                "description": description,
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


async def _user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    return result.scalar_one_or_none()


async def handle_stripe_webhook(db: AsyncSession, payload: bytes, sig_header: str) -> None:
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    etype = event["type"]
    obj = event["data"]["object"]

    if etype == "checkout.session.completed":
        user_id = obj.get("metadata", {}).get("user_id")
        plan = obj.get("metadata", {}).get("plan", "indie")
        if user_id:
            user = await _user_by_id(db, user_id)
            if user:
                sub = await apply_plan(db, user, plan, confirmed_payment=True)
                sub.stripe_customer_id = obj.get("customer")
                sub.stripe_subscription_id = obj.get("subscription")

    elif etype in ("customer.subscription.updated", "customer.subscription.deleted"):
        sub_id = obj.get("id")
        result = await db.execute(select(Subscription).where(Subscription.stripe_subscription_id == sub_id))
        sub = result.scalar_one_or_none()
        if not sub:
            return
        if etype == "customer.subscription.deleted" or obj.get("status") in ("canceled", "unpaid"):
            sub.plan = PlanType.FREE
            sub.status = SubscriptionStatus.CANCELED
            sub.generations_limit = settings.FREE_GENERATIONS
        elif obj.get("status") == "active":
            sub.status = SubscriptionStatus.ACTIVE
            # map price → plan if metadata present
            items = (obj.get("items") or {}).get("data") or []
            price_id = (items[0].get("price") or {}).get("id") if items else None
            if price_id == settings.STRIPE_PRICE_STUDIO:
                sub.plan = PlanType.STUDIO
                sub.generations_limit = settings.STUDIO_GENERATIONS
            elif price_id == settings.STRIPE_PRICE_INDIE:
                sub.plan = PlanType.INDIE
                sub.generations_limit = settings.INDIE_GENERATIONS
        await db.flush()

    elif etype == "invoice.paid":
        sub_id = obj.get("subscription")
        if sub_id:
            result = await db.execute(select(Subscription).where(Subscription.stripe_subscription_id == sub_id))
            sub = result.scalar_one_or_none()
            if sub:
                sub.status = SubscriptionStatus.ACTIVE
                await db.flush()

    elif etype == "invoice.payment_failed":
        sub_id = obj.get("subscription")
        if sub_id:
            result = await db.execute(select(Subscription).where(Subscription.stripe_subscription_id == sub_id))
            sub = result.scalar_one_or_none()
            if sub:
                sub.status = SubscriptionStatus.PAST_DUE
                await db.flush()


async def handle_yukassa_notification(db: AsyncSession, payload: dict[str, Any]) -> None:
    """YuKassa payment notification (HTTP notifications)."""
    event = payload.get("event") or payload.get("type")
    obj = payload.get("object") or {}
    if event not in ("payment.succeeded", "payment.waiting_for_capture"):
        if event == "payment.canceled":
            return
        # Some payloads nest differently
        if obj.get("status") != "succeeded":
            return

    if obj.get("status") and obj.get("status") != "succeeded":
        return

    meta = obj.get("metadata") or {}
    user_id = meta.get("user_id")
    plan = meta.get("plan", "indie")
    if not user_id:
        return
    user = await _user_by_id(db, user_id)
    if user:
        sub = await apply_plan(db, user, plan, confirmed_payment=True)
        sub.yukassa_payment_id = obj.get("id")
        await db.flush()
