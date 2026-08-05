"""Track generations, XP, and achievements."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.achievement import Achievement, UserAchievement
from app.models.generation import Generation, GenerationStatus, ToolType
from app.models.user import User
from app.services.ai_costing import estimate_cost_usd
from app.services.openai_client import LlmUsage

XP_PER_GENERATION = 10

ACHIEVEMENT_THRESHOLDS = [
    ("first_forge", "First Forge", "Complete your first generation", 1, 25),
    ("apprentice", "Apprentice", "Complete 10 generations", 10, 50),
    ("artisan", "Artisan", "Complete 50 generations", 50, 150),
    ("master", "Master Craftsman", "Complete 100 generations", 100, 300),
    ("legend", "Legend", "Complete 500 generations", 500, 1000),
]


def current_month_key(now: Optional[datetime] = None) -> str:
    now = now or datetime.now(timezone.utc)
    return f"{now.year:04d}-{now.month:02d}"


def ensure_monthly_counters(user: User, now: Optional[datetime] = None) -> None:
    """Reset monthly XP / generation counters when the calendar month changes."""
    now = now or datetime.now(timezone.utc)
    key = current_month_key(now)
    if user.xp_month_key != key:
        user.xp_this_month = 0
        user.xp_month_key = key
    if user.generation_reset_at is None or (
        user.generation_reset_at.year != now.year or user.generation_reset_at.month != now.month
    ):
        user.generations_this_month = 0
        user.generation_reset_at = now


async def create_generation(
    db: AsyncSession,
    user: User,
    tool: ToolType,
    input_data: dict[str, Any],
    project_id: Optional[UUID] = None,
    title: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> Generation:
    gen = Generation(
        user_id=user.id,
        project_id=project_id,
        tool=tool,
        status=GenerationStatus.PROCESSING,
        title=title or tool.value.replace("_", " ").title(),
        input_data=input_data,
        client_ip=client_ip,
    )
    db.add(gen)
    await db.flush()
    return gen


def apply_usage_metrics(
    generation: Generation,
    *,
    duration_ms: Optional[int] = None,
    usage: Optional[LlmUsage] = None,
    pricing: Optional[dict[str, Any]] = None,
) -> None:
    if duration_ms is not None:
        generation.duration_ms = duration_ms
    if usage is None:
        return
    generation.prompt_tokens = usage.prompt_tokens or None
    generation.completion_tokens = usage.completion_tokens or None
    generation.model_name = usage.model_name
    cost = estimate_cost_usd(usage, pricing)
    generation.cost_usd = cost if cost > 0 else Decimal("0")


async def complete_generation(
    db: AsyncSession,
    generation: Generation,
    user: User,
    output_data: dict[str, Any],
    asset_urls: Optional[list] = None,
    *,
    duration_ms: Optional[int] = None,
    usage: Optional[LlmUsage] = None,
    pricing: Optional[dict[str, Any]] = None,
) -> Generation:
    now = datetime.now(timezone.utc)
    ensure_monthly_counters(user, now)

    generation.status = GenerationStatus.COMPLETED
    generation.output_data = output_data
    generation.asset_urls = asset_urls
    generation.completed_at = now
    generation.xp_awarded = XP_PER_GENERATION
    apply_usage_metrics(generation, duration_ms=duration_ms, usage=usage, pricing=pricing)

    user.xp += XP_PER_GENERATION
    user.xp_this_month = (user.xp_this_month or 0) + XP_PER_GENERATION
    user.total_generations += 1
    # generations_this_month is reserved atomically before work starts

    # Bump org shared counter if member of a studio org
    from app.models.organization import Organization, OrgMembership

    mem = await db.execute(
        select(OrgMembership).where(OrgMembership.user_id == user.id).limit(1)
    )
    membership = mem.scalar_one_or_none()
    if membership:
        org = await db.get(Organization, membership.organization_id)
        if org:
            if org.generation_reset_at is None or (
                org.generation_reset_at.year != now.year or org.generation_reset_at.month != now.month
            ):
                org.generations_this_month = 0
                org.generation_reset_at = now
            org.generations_this_month += 1

    await _check_achievements(db, user)
    await db.flush()
    return generation


async def fail_generation(
    db: AsyncSession,
    generation: Generation,
    error: str,
    *,
    duration_ms: Optional[int] = None,
) -> Generation:
    generation.status = GenerationStatus.FAILED
    generation.error_message = error
    generation.completed_at = datetime.now(timezone.utc)
    if duration_ms is not None:
        generation.duration_ms = duration_ms
    await db.flush()
    return generation


async def _check_achievements(db: AsyncSession, user: User) -> None:
    result = await db.execute(select(Achievement))
    achievements = {a.code: a for a in result.scalars().all()}

    if not achievements:
        for code, name, desc, threshold, xp in ACHIEVEMENT_THRESHOLDS:
            a = Achievement(code=code, name=name, description=desc, threshold=threshold, xp_reward=xp)
            db.add(a)
        await db.flush()
        result = await db.execute(select(Achievement))
        achievements = {a.code: a for a in result.scalars().all()}

    owned = await db.execute(select(UserAchievement.achievement_id).where(UserAchievement.user_id == user.id))
    owned_ids = set(owned.scalars().all())

    for ach in achievements.values():
        if ach.id in owned_ids:
            continue
        if user.total_generations >= ach.threshold:
            db.add(UserAchievement(user_id=user.id, achievement_id=ach.id))
            user.xp += ach.xp_reward
            user.xp_this_month = (user.xp_this_month or 0) + ach.xp_reward


async def get_user_achievements(db: AsyncSession, user_id: UUID) -> list[dict[str, Any]]:
    result = await db.execute(
        select(UserAchievement)
        .options(selectinload(UserAchievement.achievement))
        .where(UserAchievement.user_id == user_id)
    )
    rows = result.scalars().all()
    return [
        {
            "code": ua.achievement.code,
            "name": ua.achievement.name,
            "description": ua.achievement.description,
            "icon": ua.achievement.icon,
            "xp_reward": ua.achievement.xp_reward,
            "unlocked_at": ua.unlocked_at.isoformat() if ua.unlocked_at else None,
        }
        for ua in rows
    ]
