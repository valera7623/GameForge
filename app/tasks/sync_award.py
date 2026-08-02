"""Shared sync helpers for Celery workers."""

from datetime import datetime, timezone

from app.models.generation import Generation, GenerationStatus
from app.models.user import User
from app.services.generation_tracker import XP_PER_GENERATION, current_month_key


def award_generation_sync(session, gen: Generation, user: User, result: dict) -> None:
    now = datetime.now(timezone.utc)
    key = current_month_key(now)
    if getattr(user, "xp_month_key", None) != key:
        user.xp_this_month = 0
        user.xp_month_key = key
    if user.generation_reset_at is None or (
        user.generation_reset_at.year != now.year or user.generation_reset_at.month != now.month
    ):
        user.generations_this_month = 0
        user.generation_reset_at = now

    gen.status = GenerationStatus.COMPLETED
    gen.output_data = result
    gen.asset_urls = [result.get("url")] if result.get("url") else result.get("asset_urls")
    gen.completed_at = now
    gen.xp_awarded = XP_PER_GENERATION
    user.xp += XP_PER_GENERATION
    user.xp_this_month = (user.xp_this_month or 0) + XP_PER_GENERATION
    user.total_generations += 1
    user.generations_this_month += 1
