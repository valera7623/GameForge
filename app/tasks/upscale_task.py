"""Celery task: texture upscale."""

import asyncio
import base64
import time
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
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.models.generation import Generation
    from app.models.user import User
    from app.services.ai_texture_upscaler import upscale_texture
    from app.services.openai_client import begin_llm_usage, reset_llm_usage
    from app.services.ops_logs import record_error_sync
    from app.tasks.db import get_sync_engine
    from app.tasks.sync_award import award_generation_sync, fail_generation_sync

    engine = get_sync_engine()
    begin_llm_usage()
    t0 = time.perf_counter()
    try:
        image_bytes = base64.b64decode(image_b64)
        result = _run(upscale_texture(image_bytes, filename, scale, enhance))
        duration_ms = int((time.perf_counter() - t0) * 1000)
        with Session(engine) as session:
            gen = session.execute(select(Generation).where(Generation.id == UUID(generation_id))).scalar_one()
            user = session.execute(select(User).where(User.id == gen.user_id)).scalar_one()
            award_generation_sync(session, gen, user, result, duration_ms=duration_ms)
            session.commit()
        return result
    except Exception as exc:
        duration_ms = int((time.perf_counter() - t0) * 1000)
        if self.request.retries >= self.max_retries:
            with Session(engine) as session:
                gen = session.execute(
                    select(Generation).where(Generation.id == UUID(generation_id))
                ).scalar_one_or_none()
                if gen:
                    fail_generation_sync(session, gen, str(exc), duration_ms=duration_ms)
                    record_error_sync(
                        session,
                        source="celery",
                        message=str(exc),
                        status_code=502,
                        generation_id=gen.id,
                        user_id=gen.user_id,
                    )
                    session.commit()
            raise
        raise self.retry(exc=exc, countdown=10)
    finally:
        reset_llm_usage()
