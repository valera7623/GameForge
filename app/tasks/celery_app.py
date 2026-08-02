"""Celery application."""

from celery import Celery

from app.config import get_settings

settings = get_settings()

if settings.SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.APP_ENV,
            integrations=[CeleryIntegration()],
            traces_sample_rate=0.1,
        )
    except Exception:
        pass

celery_app = Celery(
    "gamedev_toolkit",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.upscale_task",
        "app.tasks.character_task",
        "app.tasks.sound_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
