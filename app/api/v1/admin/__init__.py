"""Admin API — staff-only management endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.admin.schemas import (
    AdminGenerationListOut,
    AdminGenerationOut,
    AdminMeOut,
    AdminRoleUpdate,
    AdminSubscriptionListOut,
    AdminSubscriptionOut,
    AdminToolOut,
    AdminToolsOut,
    AdminToolUpdate,
    AdminUserListOut,
    AdminUserOut,
    AdminUserUpdate,
    DashboardOut,
    GeneralSettingsOut,
    GeneralSettingsUpdate,
    GenerationStatsOut,
)
from app.config import get_settings
from app.core.rbac import (
    PERMISSIONS,
    can_assign_role,
    require_permission,
    require_staff,
)
from app.database import get_db
from app.models.generation import Generation, GenerationStatus, ToolType
from app.models.platform_setting import SETTING_GENERAL, SETTING_TOOLS
from app.models.subscription import PlanType, Subscription, SubscriptionStatus
from app.models.user import User, UserRole
from app.services.billing_service import PLANS
from app.services.platform_settings import (
    get_general_settings,
    get_tools_settings,
    set_setting,
)

settings = get_settings()
router = APIRouter(prefix="/admin", tags=["admin"])


def _user_out(user: User) -> AdminUserOut:
    sub = user.subscription
    return AdminUserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        is_verified=user.is_verified,
        plan=sub.plan.value if sub else None,
        generations_this_month=user.generations_this_month,
        generations_limit=sub.generations_limit if sub else settings.FREE_GENERATIONS,
        total_generations=user.total_generations,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def _gen_out(gen: Generation, email: Optional[str] = None) -> AdminGenerationOut:
    return AdminGenerationOut(
        id=gen.id,
        user_id=gen.user_id,
        user_email=email,
        tool=gen.tool.value,
        status=gen.status.value,
        title=gen.title,
        input_data=gen.input_data or {},
        output_data=gen.output_data,
        error_message=gen.error_message,
        xp_awarded=gen.xp_awarded,
        project_id=gen.project_id,
        created_at=gen.created_at,
        completed_at=gen.completed_at,
    )


def _sub_out(sub: Subscription, email: Optional[str] = None) -> AdminSubscriptionOut:
    return AdminSubscriptionOut(
        id=sub.id,
        user_id=sub.user_id,
        user_email=email,
        plan=sub.plan.value,
        status=sub.status.value,
        generations_limit=sub.generations_limit,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        stripe_subscription_id=sub.stripe_subscription_id,
        created_at=sub.created_at,
    )


@router.get("/auth/me", response_model=AdminMeOut)
async def admin_me(user: User = Depends(require_staff)):
    perms = [p for p, roles in PERMISSIONS.items() if user.role in roles]
    return AdminMeOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        permissions=perms,
    )


@router.get("/dashboard", response_model=DashboardOut)
async def dashboard(
    user: User = Depends(require_permission("dashboard:read")),
    db: AsyncSession = Depends(get_db),
):
    users_total = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    generations_total = (await db.execute(select(func.count()).select_from(Generation))).scalar_one()

    # Revenue proxy: active paid subscriptions × plan monthly price
    revenue = 0.0
    result = await db.execute(
        select(Subscription.plan, func.count())
        .where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.plan.in_([PlanType.INDIE, PlanType.STUDIO, PlanType.ENTERPRISE]),
        )
        .group_by(Subscription.plan)
    )
    for plan, count in result.all():
        key = plan.value if hasattr(plan, "value") else str(plan)
        cents = PLANS.get(key, {}).get("price_cents", 0) or 0
        revenue += (cents / 100.0) * count

    since = datetime.now(timezone.utc) - timedelta(days=7)
    active_users = (
        await db.execute(
            select(func.count(func.distinct(Generation.user_id))).where(Generation.created_at >= since)
        )
    ).scalar_one()
    activity_pct = round((active_users / users_total) * 100, 1) if users_total else 0.0

    day_rows = await db.execute(
        select(func.date_trunc("day", Generation.created_at).label("day"), func.count())
        .where(Generation.created_at >= since)
        .group_by("day")
        .order_by("day")
    )
    series = [{"date": row[0].date().isoformat() if row[0] else "", "count": row[1]} for row in day_rows.all()]

    recent = await db.execute(
        select(User).options(selectinload(User.subscription)).order_by(User.created_at.desc()).limit(8)
    )
    recent_users = [
        {
            "id": str(u.id),
            "email": u.email,
            "role": u.role.value,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "plan": u.subscription.plan.value if u.subscription else None,
        }
        for u in recent.scalars().all()
    ]

    return DashboardOut(
        users_total=users_total,
        generations_total=generations_total,
        revenue_usd_estimate=round(revenue, 2),
        activity_pct=activity_pct,
        generations_last_7_days=series,
        recent_users=recent_users,
    )


@router.get("/users", response_model=AdminUserListOut)
async def list_users(
    q: Optional[str] = None,
    role: Optional[str] = None,
    plan: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_permission("users:read")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).options(selectinload(User.subscription))
    count_stmt = select(func.count()).select_from(User)
    if q:
        like = f"%{q.lower()}%"
        filt = func.lower(User.email).like(like) | func.lower(func.coalesce(User.full_name, "")).like(like)
        stmt = stmt.where(filt)
        count_stmt = count_stmt.where(filt)
    if role:
        try:
            role_enum = UserRole(role)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid role") from exc
        stmt = stmt.where(User.role == role_enum)
        count_stmt = count_stmt.where(User.role == role_enum)
    if plan:
        try:
            plan_enum = PlanType(plan)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid plan") from exc
        stmt = stmt.join(Subscription).where(Subscription.plan == plan_enum)
        count_stmt = select(func.count()).select_from(User).join(Subscription).where(Subscription.plan == plan_enum)

    total = (await db.execute(count_stmt)).scalar_one()
    rows = await db.execute(
        stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = [_user_out(u) for u in rows.scalars().unique().all()]
    return AdminUserListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/users/{user_id}", response_model=AdminUserOut)
async def get_user(
    user_id: UUID,
    user: User = Depends(require_permission("users:read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).options(selectinload(User.subscription)).where(User.id == user_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_out(target)


@router.put("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: UUID,
    body: AdminUserUpdate,
    actor: User = Depends(require_permission("users:write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).options(selectinload(User.subscription)).where(User.id == user_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if body.full_name is not None:
        target.full_name = body.full_name
    if body.is_verified is not None:
        target.is_verified = body.is_verified
    await db.flush()
    return _user_out(target)


@router.post("/users/{user_id}/block", response_model=AdminUserOut)
async def block_user(
    user_id: UUID,
    actor: User = Depends(require_permission("users:write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).options(selectinload(User.subscription)).where(User.id == user_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == actor.id:
        raise HTTPException(status_code=400, detail="Cannot block yourself")
    if target.role == UserRole.SUPER_ADMIN and actor.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Cannot block super_admin")
    target.is_active = False
    await db.flush()
    return _user_out(target)


@router.post("/users/{user_id}/unblock", response_model=AdminUserOut)
async def unblock_user(
    user_id: UUID,
    actor: User = Depends(require_permission("users:write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).options(selectinload(User.subscription)).where(User.id == user_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    target.is_active = True
    await db.flush()
    return _user_out(target)


@router.post("/users/{user_id}/role", response_model=AdminUserOut)
async def set_user_role(
    user_id: UUID,
    body: AdminRoleUpdate,
    actor: User = Depends(require_permission("users:role")),
    db: AsyncSession = Depends(get_db),
):
    try:
        new_role = UserRole(body.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid role") from exc
    if not can_assign_role(actor, new_role):
        raise HTTPException(status_code=403, detail="Cannot assign this role")

    result = await db.execute(
        select(User).options(selectinload(User.subscription)).where(User.id == user_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role == UserRole.SUPER_ADMIN and actor.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Cannot change super_admin role")
    if target.id == actor.id and new_role not in (UserRole.SUPER_ADMIN, UserRole.ADMIN):
        raise HTTPException(status_code=400, detail="Cannot demote yourself this way")

    target.role = new_role
    await db.flush()
    return _user_out(target)


@router.get("/generations/stats", response_model=GenerationStatsOut)
async def generation_stats(
    user: User = Depends(require_permission("generations:read")),
    db: AsyncSession = Depends(get_db),
):
    total = (await db.execute(select(func.count()).select_from(Generation))).scalar_one()
    by_tool = await db.execute(select(Generation.tool, func.count()).group_by(Generation.tool))
    by_status = await db.execute(select(Generation.status, func.count()).group_by(Generation.status))
    since = datetime.now(timezone.utc) - timedelta(days=7)
    day_rows = await db.execute(
        select(func.date_trunc("day", Generation.created_at).label("day"), func.count())
        .where(Generation.created_at >= since)
        .group_by("day")
        .order_by("day")
    )
    return GenerationStatsOut(
        total=total,
        by_tool=[{"tool": t.value, "count": c} for t, c in by_tool.all()],
        by_status=[{"status": s.value, "count": c} for s, c in by_status.all()],
        last_7_days=[{"date": r[0].date().isoformat() if r[0] else "", "count": r[1]} for r in day_rows.all()],
    )


@router.get("/generations", response_model=AdminGenerationListOut)
async def list_generations(
    tool: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    q: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_permission("generations:read")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Generation, User.email).join(User, User.id == Generation.user_id)
    count_stmt = select(func.count()).select_from(Generation)
    if tool:
        try:
            tool_enum = ToolType(tool)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid tool") from exc
        stmt = stmt.where(Generation.tool == tool_enum)
        count_stmt = count_stmt.where(Generation.tool == tool_enum)
    if status_filter:
        try:
            st = GenerationStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid status") from exc
        stmt = stmt.where(Generation.status == st)
        count_stmt = count_stmt.where(Generation.status == st)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(User.email).like(like))
        count_stmt = (
            select(func.count())
            .select_from(Generation)
            .join(User, User.id == Generation.user_id)
            .where(func.lower(User.email).like(like))
        )

    total = (await db.execute(count_stmt)).scalar_one()
    rows = await db.execute(
        stmt.order_by(Generation.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = [_gen_out(g, email) for g, email in rows.all()]
    return AdminGenerationListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/generations/user/{user_id}", response_model=AdminGenerationListOut)
async def generations_for_user(
    user_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_permission("generations:read")),
    db: AsyncSession = Depends(get_db),
):
    total = (
        await db.execute(select(func.count()).select_from(Generation).where(Generation.user_id == user_id))
    ).scalar_one()
    rows = await db.execute(
        select(Generation, User.email)
        .join(User, User.id == Generation.user_id)
        .where(Generation.user_id == user_id)
        .order_by(Generation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_gen_out(g, email) for g, email in rows.all()]
    return AdminGenerationListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/generations/{gen_id}", response_model=AdminGenerationOut)
async def get_generation(
    gen_id: UUID,
    user: User = Depends(require_permission("generations:read")),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        select(Generation, User.email).join(User, User.id == Generation.user_id).where(Generation.id == gen_id)
    )
    pair = row.one_or_none()
    if not pair:
        raise HTTPException(status_code=404, detail="Generation not found")
    gen, email = pair
    return _gen_out(gen, email)


@router.get("/subscriptions", response_model=AdminSubscriptionListOut)
async def list_subscriptions(
    plan: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_permission("users:read")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Subscription, User.email).join(User, User.id == Subscription.user_id)
    count_stmt = select(func.count()).select_from(Subscription)
    if plan:
        try:
            plan_enum = PlanType(plan)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid plan") from exc
        stmt = stmt.where(Subscription.plan == plan_enum)
        count_stmt = count_stmt.where(Subscription.plan == plan_enum)
    if status_filter:
        try:
            st = SubscriptionStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid status") from exc
        stmt = stmt.where(Subscription.status == st)
        count_stmt = count_stmt.where(Subscription.status == st)

    total = (await db.execute(count_stmt)).scalar_one()
    rows = await db.execute(
        stmt.order_by(Subscription.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = [_sub_out(s, email) for s, email in rows.all()]
    return AdminSubscriptionListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/subscriptions/{sub_id}", response_model=AdminSubscriptionOut)
async def get_subscription(
    sub_id: UUID,
    user: User = Depends(require_permission("users:read")),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        select(Subscription, User.email)
        .join(User, User.id == Subscription.user_id)
        .where(Subscription.id == sub_id)
    )
    pair = row.one_or_none()
    if not pair:
        raise HTTPException(status_code=404, detail="Subscription not found")
    sub, email = pair
    return _sub_out(sub, email)


@router.post("/subscriptions/{sub_id}/cancel", response_model=AdminSubscriptionOut)
async def cancel_subscription(
    sub_id: UUID,
    actor: User = Depends(require_permission("subscriptions:write")),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        select(Subscription, User.email)
        .join(User, User.id == Subscription.user_id)
        .where(Subscription.id == sub_id)
    )
    pair = row.one_or_none()
    if not pair:
        raise HTTPException(status_code=404, detail="Subscription not found")
    sub, email = pair

    if sub.stripe_subscription_id and settings.STRIPE_SECRET_KEY:
        try:
            import stripe

            stripe.api_key = settings.STRIPE_SECRET_KEY
            stripe.Subscription.cancel(sub.stripe_subscription_id)
        except Exception:
            pass  # best-effort; still mark canceled locally

    sub.status = SubscriptionStatus.CANCELED
    sub.plan = PlanType.FREE
    sub.generations_limit = settings.FREE_GENERATIONS
    await db.flush()
    return _sub_out(sub, email)


@router.get("/tools", response_model=AdminToolsOut)
async def list_tools(
    user: User = Depends(require_permission("dashboard:read")),
    db: AsyncSession = Depends(get_db),
):
    tools = await get_tools_settings(db)
    return AdminToolsOut(
        tools=[
            AdminToolOut(name=name, display_name=meta["display_name"], enabled=meta["enabled"])
            for name, meta in tools.items()
        ]
    )


@router.post("/tools/{name}/toggle", response_model=AdminToolOut)
async def toggle_tool(
    name: str,
    actor: User = Depends(require_permission("tools:write")),
    db: AsyncSession = Depends(get_db),
):
    tools = await get_tools_settings(db)
    if name not in tools:
        raise HTTPException(status_code=404, detail="Unknown tool")
    tools[name]["enabled"] = not tools[name]["enabled"]
    await set_setting(db, SETTING_TOOLS, tools)
    meta = tools[name]
    return AdminToolOut(name=name, display_name=meta["display_name"], enabled=meta["enabled"])


@router.put("/tools/{name}", response_model=AdminToolOut)
async def update_tool(
    name: str,
    body: AdminToolUpdate,
    actor: User = Depends(require_permission("tools:write")),
    db: AsyncSession = Depends(get_db),
):
    tools = await get_tools_settings(db)
    if name not in tools:
        raise HTTPException(status_code=404, detail="Unknown tool")
    if body.display_name is not None:
        tools[name]["display_name"] = body.display_name
    if body.enabled is not None:
        tools[name]["enabled"] = body.enabled
    await set_setting(db, SETTING_TOOLS, tools)
    meta = tools[name]
    return AdminToolOut(name=name, display_name=meta["display_name"], enabled=meta["enabled"])


@router.get("/settings", response_model=GeneralSettingsOut)
async def get_settings_endpoint(
    user: User = Depends(require_permission("settings:read")),
    db: AsyncSession = Depends(get_db),
):
    general = await get_general_settings(db)
    return GeneralSettingsOut(
        app_name=general.get("app_name") or "GameForge",
        domain=general.get("domain") or "gameforge.website",
        notes=general.get("notes") or "",
    )


@router.put("/settings", response_model=GeneralSettingsOut)
async def put_settings(
    body: GeneralSettingsUpdate,
    actor: User = Depends(require_permission("settings:write")),
    db: AsyncSession = Depends(get_db),
):
    general = await get_general_settings(db)
    if body.app_name is not None:
        general["app_name"] = body.app_name
    if body.domain is not None:
        general["domain"] = body.domain
    if body.notes is not None:
        general["notes"] = body.notes
    await set_setting(db, SETTING_GENERAL, general)
    return GeneralSettingsOut(
        app_name=general.get("app_name") or "GameForge",
        domain=general.get("domain") or "gameforge.website",
        notes=general.get("notes") or "",
    )
