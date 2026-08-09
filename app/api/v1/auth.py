"""Auth endpoints: register, login, password reset, API keys, cookie sessions."""

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.auth_tokens import (
    clear_auth_cookies,
    issue_tokens,
    revoke_refresh,
    rotate_refresh,
    set_auth_cookies,
)
from app.core.rate_limiter import rate_limit
from app.core.security import hash_api_key, hash_password, hash_token, verify_password
from app.database import get_db
from app.deps import get_current_user
from app.models.subscription import PlanType, Subscription, SubscriptionStatus
from app.models.user import APIKey, User
from app.schemas import (
    APIKeyCreate,
    APIKeyResponse,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserMeResponse,
)
from app.services.billing_service import get_or_create_subscription
from app.services.generation_tracker import get_user_achievements

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _token_response(access: str, refresh: str, response: Response) -> TokenResponse:
    set_auth_cookies(response, access, refresh)
    # Body tokens kept for API clients / mobile; browsers should prefer cookies.
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    await rate_limit(request, settings.AUTH_RATE_LIMIT_PER_MINUTE)
    existing = await db.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    source = (body.signup_source or "").strip()[:64] or None
    pack = (body.signup_pack or "").strip()[:32] or None
    attribution = body.attribution if isinstance(body.attribution, dict) else None
    if attribution:
        # Keep payload small / PII-free
        attribution = {str(k)[:40]: str(v)[:200] for k, v in list(attribution.items())[:20] if v is not None}

    user = User(
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        is_verified=True,
        generation_reset_at=datetime.now(timezone.utc),
        signup_source=source,
        signup_pack=pack,
        attribution=attribution,
    )
    db.add(user)
    await db.flush()

    db.add(
        Subscription(
            user_id=user.id,
            plan=PlanType.FREE,
            status=SubscriptionStatus.ACTIVE,
            generations_limit=settings.FREE_GENERATIONS,
            current_period_start=datetime.now(timezone.utc),
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        )
    )
    await db.flush()

    from app.services.email_service import send_locforge_welcome, send_welcome

    try:
        if source == "locforge":
            await send_locforge_welcome(user.email, user.full_name, pack)
        else:
            await send_welcome(user.email, user.full_name)
    except Exception:
        pass

    access, refresh = await issue_tokens(db, user)
    return _token_response(access, refresh, response)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    await rate_limit(request, settings.AUTH_RATE_LIMIT_PER_MINUTE)
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    user.last_login_at = datetime.now(timezone.utc)
    access, refresh = await issue_tokens(db, user)
    return _token_response(access, refresh, response)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    body: RefreshRequest = RefreshRequest(),
    db: AsyncSession = Depends(get_db),
):
    await rate_limit(request, settings.AUTH_RATE_LIMIT_PER_MINUTE)
    token = body.refresh_token or request.cookies.get(settings.REFRESH_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    try:
        _user, access, new_refresh = await rotate_refresh(db, token)
    except ValueError as exc:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return _token_response(access, new_refresh, response)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    body: RefreshRequest = RefreshRequest(),
    db: AsyncSession = Depends(get_db),
):
    from app.deps import resolve_user_from_request

    token = body.refresh_token or request.cookies.get(settings.REFRESH_COOKIE)
    user = await resolve_user_from_request(request, db, required=False)
    await revoke_refresh(db, token, user.id if user else None)
    clear_auth_cookies(response)
    return {"message": "Logged out"}


@router.post("/password-reset/request")
async def password_reset_request(
    body: PasswordResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await rate_limit(request, settings.AUTH_RATE_LIMIT_PER_MINUTE)
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    resp = {"message": "If the email exists, a reset link was sent"}
    if user:
        token = secrets.token_urlsafe(32)
        user.reset_token = hash_token(token)
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(
            minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES
        )
        from app.services.email_service import send_password_reset

        await send_password_reset(user.email, token)
        if settings.DEBUG and not settings.is_production:
            resp["reset_token"] = token
    return resp


@router.post("/password-reset/confirm")
async def password_reset_confirm(
    body: PasswordResetConfirm,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await rate_limit(request, settings.AUTH_RATE_LIMIT_PER_MINUTE)
    token_hash = hash_token(body.token)
    result = await db.execute(select(User).where(User.reset_token == token_hash))
    user = result.scalar_one_or_none()
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user.hashed_password = hash_password(body.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    return {"message": "Password updated"}


@router.get("/me", response_model=UserMeResponse)
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    sub = await get_or_create_subscription(db, user)
    achievements = await get_user_achievements(db, user.id)
    return UserMeResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        xp=user.xp,
        total_generations=user.total_generations,
        generations_this_month=user.generations_this_month,
        is_active=user.is_active,
        created_at=user.created_at,
        plan=sub.plan.value,
        generations_limit=sub.generations_limit,
        achievements_count=len(achievements),
        localization_words_remaining=int(sub.localization_words_remaining or 0),
        signup_source=user.signup_source,
        signup_pack=user.signup_pack,
    )


@router.post("/api-keys", response_model=APIKeyResponse, status_code=201)
async def create_api_key(
    body: APIKeyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    raw = APIKey.generate_key()
    key = APIKey(
        user_id=user.id,
        name=body.name,
        key_prefix=raw[:12],
        key_hash=hash_api_key(raw),
    )
    db.add(key)
    await db.flush()
    return APIKeyResponse(
        id=key.id,
        name=key.name,
        key_prefix=key.key_prefix,
        key=raw,
        created_at=key.created_at,
    )


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(APIKey).where(APIKey.user_id == user.id))
    keys = result.scalars().all()
    return [
        APIKeyResponse(id=k.id, name=k.name, key_prefix=k.key_prefix, key=None, created_at=k.created_at)
        for k in keys
    ]


@router.delete("/api-keys/{key_id}", status_code=204)
async def delete_api_key(
    key_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user.id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    await db.delete(key)
    return Response(status_code=204)
