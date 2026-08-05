"""Celery task: purge ops logs older than retention."""

from app.tasks.celery_app import celery_app


@celery_app.task(name="tasks.purge_ops_logs")
def purge_ops_logs_task():
    from sqlalchemy.orm import Session

    from app.services.ops_logs import purge_ops_logs_sync
    from app.tasks.db import get_sync_engine

    engine = get_sync_engine()
    with Session(engine) as session:
        counts = purge_ops_logs_sync(session)
        session.commit()
    return counts
