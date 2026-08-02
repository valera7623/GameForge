"""Billing endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limiter import rate_limit
from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas import CheckoutRequest, CheckoutResponse, PlanInfo
from app.services import billing_service

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanInfo])
async def plans():
    return [PlanInfo(**p) for p in billing_service.list_plans()]


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(
    body: CheckoutRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await rate_limit(request)
    try:
        result = await billing_service.create_checkout(
            db, user, body.plan, body.provider, body.success_url, body.cancel_url
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CheckoutResponse(checkout_url=result["checkout_url"], session_id=result.get("session_id"))


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        await billing_service.handle_stripe_webhook(db, payload, sig)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/webhook/yukassa")
async def yukassa_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.json()
    try:
        await billing_service.handle_yukassa_notification(db, payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/portal")
async def customer_portal(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        return await billing_service.create_customer_portal(db, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/cancel")
async def cancel(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        sub = await billing_service.cancel_subscription(db, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"plan": sub.plan.value, "status": sub.status.value}


@router.get("/subscription")
async def my_subscription(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    sub = await billing_service.get_or_create_subscription(db, user)
    return {
        "plan": sub.plan.value,
        "status": sub.status.value,
        "generations_limit": sub.generations_limit,
        "current_period_end": sub.current_period_end,
    }
