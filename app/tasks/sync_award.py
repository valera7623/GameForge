"""Shared sync helpers for Celery workers — mirrors async award path."""

from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.achievement import Achievement, UserAchievement
from app.models.generation import Generation, GenerationStatus
from app.models.organization import Organization, OrgMembership
from app.models.user import User
from app.services.generation_tracker import ACHIEVEMENT_THRESHOLDS, XP_PER_GENERATION, current_month_key


def award_generation_sync(session: Session, gen: Generation, user: User, result: dict) -> None:
    now = datetime.now(timezone.utc)
    key = current_month_key(now)
    if getattr(user, "xp_month_key", None) != key:
        user.xp_this_month = 0
        user.xp_month_key = key

    gen.status = GenerationStatus.COMPLETED
    gen.output_data = result
    gen.asset_urls = [result.get("url")] if result.get("url") else result.get("asset_urls")
    gen.completed_at = now
    gen.xp_awarded = XP_PER_GENERATION
    user.xp += XP_PER_GENERATION
    user.xp_this_month = (user.xp_this_month or 0) + XP_PER_GENERATION
    user.total_generations += 1

    mem = session.execute(select(OrgMembership).where(OrgMembership.user_id == user.id).limit(1)).scalar_one_or_none()
    if mem:
        org = session.get(Organization, mem.organization_id)
        if org:
            if org.generation_reset_at is None or (
                org.generation_reset_at.year != now.year or org.generation_reset_at.month != now.month
            ):
                org.generations_this_month = 0
                org.generation_reset_at = now
            org.generations_this_month += 1

    _check_achievements_sync(session, user)


def refund_quota_sync(session: Session, user_id) -> None:
    session.execute(
        text(
            """
            UPDATE users
            SET generations_this_month = GREATEST(generations_this_month - 1, 0)
            WHERE id = :uid
            """
        ),
        {"uid": str(user_id)},
    )


def fail_generation_sync(session: Session, gen: Generation, error: str) -> None:
    gen.status = GenerationStatus.FAILED
    gen.error_message = error
    gen.completed_at = datetime.now(timezone.utc)
    refund_quota_sync(session, gen.user_id)


def _check_achievements_sync(session: Session, user: User) -> None:
    achievements = {a.code: a for a in session.execute(select(Achievement)).scalars().all()}
    owned = {
        ua.achievement_id
        for ua in session.execute(select(UserAchievement).where(UserAchievement.user_id == user.id)).scalars().all()
    }
    for code, _name, _desc, threshold, xp in ACHIEVEMENT_THRESHOLDS:
        ach = achievements.get(code)
        if not ach or ach.id in owned:
            continue
        if user.total_generations >= threshold:
            session.add(UserAchievement(user_id=user.id, achievement_id=ach.id))
            user.xp += xp
            user.xp_this_month = (user.xp_this_month or 0) + xp
