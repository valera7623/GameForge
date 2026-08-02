"""Celery task: texture upscale."""

import asyncio
import base64
from uuid import UUID

from app.tasks.celery_app import celery_app


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(name="tasks.upscale_texture", bind=True, max_retries=2)
def upscale_texture_task(self, generation_id: str, image_b64: str, filename: str, scale: int, enhance: bool):
    from datetime import datetime, timezone

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from app.config import get_settings
    from app.models.generation import Generation, GenerationStatus
    from app.models.user import User
    from app.services.ai_texture_upscaler import upscale_texture
    from app.services.generation_tracker import XP_PER_GENERATION

    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL_SYNC)

    try:
        image_bytes = base64.b64decode(image_b64)
        result = _run(upscale_texture(image_bytes, filename, scale, enhance))
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
