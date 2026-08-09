"""Dashboard, generations history, leaderboard."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.rbac import is_staff
from app.database import get_db
from app.deps import get_current_user
from app.models.generation import Generation
from app.models.project import Project
from app.models.subscription import PlanType
from app.models.user import User
from app.schemas import DashboardStats, GenerationResponse, LeaderboardEntry
from app.services.billing_service import get_or_create_subscription
from app.services.generation_tracker import current_month_key, ensure_monthly_counters, get_user_achievements

router = APIRouter(tags=["dashboard"])


def _can_reset_usage(user: User, plan: PlanType) -> bool:
    """Staff / enterprise may reset; everyone may in non-production (local/test)."""
    if is_staff(user) or plan == PlanType.ENTERPRISE:
        return True
    return not get_settings().is_production


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ensure_monthly_counters(user)
    sub = await get_or_create_subscription(db, user)
    projects_count = await db.scalar(select(func.count(Project.id)).where(Project.owner_id == user.id))
    result = await db.execute(
        select(Generation)
        .where(Generation.user_id == user.id)
        .order_by(Generation.created_at.desc())
        .limit(12)
    )
    recent = result.scalars().all()
    achievements = await get_user_achievements(db, user.id)

    month_key = current_month_key()
    rank = await db.scalar(
        select(func.count(User.id)).where(
            User.is_active.is_(True),
            User.xp_month_key == month_key,
            User.xp_this_month > (user.xp_this_month or 0),
        )
    )
    rank = (rank or 0) + 1

    return DashboardStats(
        total_generations=user.total_generations,
        generations_this_month=user.generations_this_month,
        generations_limit=sub.generations_limit,
        xp=user.xp,
        xp_this_month=user.xp_this_month or 0,
        plan=sub.plan.value,
        projects_count=projects_count or 0,
        recent_generations=[_gen(g) for g in recent],
        achievements=achievements,
        leaderboard_rank=rank,
        can_reset_usage=_can_reset_usage(user, sub.plan),
    )


@router.post("/dashboard/reset-usage", response_model=DashboardStats)
async def reset_usage(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Zero usage counters on the dashboard (quota / XP / totals). Does not delete projects or history."""
    sub = await get_or_create_subscription(db, user)
    if not _can_reset_usage(user, sub.plan):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reset usage is not allowed")

    now = datetime.now(timezone.utc)
    user.generations_this_month = 0
    user.generation_reset_at = now
    user.xp_this_month = 0
    user.xp_month_key = current_month_key(now)
    user.total_generations = 0
    await db.flush()
    return await dashboard(user=user, db=db)


@router.get("/generations", response_model=List[GenerationResponse])
async def list_generations(
    tool: Optional[str] = None,
    project_id: Optional[UUID] = None,
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.generation import ToolType

    q = select(Generation).where(Generation.user_id == user.id)
    if tool:
        try:
            q = q.where(Generation.tool == ToolType(tool))
        except ValueError:
            pass
    if project_id:
        q = q.where(Generation.project_id == project_id)
    q = q.order_by(Generation.created_at.desc()).limit(limit)
    result = await db.execute(q)
    return [_gen(g) for g in result.scalars().all()]


@router.get("/generations/{generation_id}", response_model=GenerationResponse)
async def get_generation(
    generation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException

    result = await db.execute(
        select(Generation).where(Generation.id == generation_id, Generation.user_id == user.id)
    )
    gen = result.scalar_one_or_none()
    if not gen:
        raise HTTPException(status_code=404, detail="Generation not found")
    return _gen(gen)


@router.delete("/generations/{generation_id}", status_code=204)
async def delete_generation(
    generation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException

    result = await db.execute(
        select(Generation).where(Generation.id == generation_id, Generation.user_id == user.id)
    )
    gen = result.scalar_one_or_none()
    if not gen:
        raise HTTPException(status_code=404, detail="Generation not found")
    await db.delete(gen)


@router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def leaderboard(
    period: str = Query("month", pattern="^(month|all)$"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Monthly leaderboard by default; period=all for lifetime XP."""
    if period == "all":
        result = await db.execute(
            select(User).where(User.is_active.is_(True)).order_by(User.xp.desc()).limit(limit)
        )
        users = result.scalars().all()
        return [_entry(i, u, u.xp) for i, u in enumerate(users, start=1)]

    month_key = current_month_key()
    result = await db.execute(
        select(User)
        .where(User.is_active.is_(True), User.xp_month_key == month_key)
        .order_by(User.xp_this_month.desc())
        .limit(limit)
    )
    users = result.scalars().all()
    return [_entry(i, u, u.xp_this_month or 0) for i, u in enumerate(users, start=1)]


def _entry(rank: int, u: User, xp: int) -> LeaderboardEntry:
    email = u.email
    masked = email[0] + "***@" + email.split("@")[-1] if "@" in email else "***"
    return LeaderboardEntry(
        rank=rank,
        user_id=u.id,
        full_name=u.full_name,
        email_masked=masked,
        xp=xp,
        total_generations=u.total_generations,
    )


def _gen(g: Generation) -> GenerationResponse:
    return GenerationResponse(
        id=g.id,
        tool=g.tool.value,
        status=g.status.value,
        title=g.title,
        input_data=g.input_data or {},
        output_data=g.output_data,
        asset_urls=g.asset_urls,
        error_message=g.error_message,
        xp_awarded=g.xp_awarded,
        project_id=g.project_id,
        created_at=g.created_at,
        completed_at=g.completed_at,
    )
