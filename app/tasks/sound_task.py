"""Celery task: sound generation."""

import asyncio
from uuid import UUID

from app.tasks.celery_app import celery_app


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(name="tasks.generate_sound", bind=True, max_retries=2)
def generate_sound_task(
    self, generation_id: str, description: str, kind: str, mood: str, duration_sec: int
):
    from datetime import datetime, timezone

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from app.config import get_settings
    from app.models.generation import Generation, GenerationStatus
    from app.models.user import User
    from app.services.ai_sound_designer import generate_sound
    from app.services.generation_tracker import XP_PER_GENERATION

    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL_SYNC)

    try:
        result = _run(generate_sound(description, kind, mood, duration_sec))
        with Session(engine) as session:
            gen = session.execute(select(Generation).where(Generation.id == UUID(generation_id))).scalar_one()
            user = session.execute(select(User).where(User.id == gen.user_id)).scalar_one()
            from app.tasks.sync_award import award_generation_sync
            award_generation_sync(session, gen, user, result)
            session.commit()
        return result
    except Exception as exc:
        with Session(engine) as session:
            gen = session.execute(
                select(Generation).where(Generation.id == UUID(generation_id))
            ).scalar_one_or_none()
            if gen:
                gen.status = GenerationStatus.FAILED
                gen.error_message = str(exc)
                gen.completed_at = datetime.now(timezone.utc)
                session.commit()
        raise self.retry(exc=exc, countdown=10)
