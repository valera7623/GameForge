"""Celery task: character generation."""

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


@celery_app.task(name="tasks.create_character", bind=True, max_retries=2)
def create_character_task(self, generation_id: str, description: str, style: str, view: str):
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.models.generation import Generation
    from app.models.user import User
    from app.services.ai_character_creator import create_character
    from app.tasks.db import get_sync_engine
    from app.tasks.sync_award import award_generation_sync, fail_generation_sync

    engine = get_sync_engine()
    try:
        result = _run(create_character(description, style, view))
        with Session(engine) as session:
            gen = session.execute(select(Generation).where(Generation.id == UUID(generation_id))).scalar_one()
            user = session.execute(select(User).where(User.id == gen.user_id)).scalar_one()
            award_generation_sync(session, gen, user, result)
            session.commit()
        return result
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            with Session(engine) as session:
                gen = session.execute(
                    select(Generation).where(Generation.id == UUID(generation_id))
                ).scalar_one_or_none()
                if gen:
                    fail_generation_sync(session, gen, str(exc))
                    session.commit()
            raise
        raise self.retry(exc=exc, countdown=10)
