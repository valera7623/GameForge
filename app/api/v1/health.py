"""Health check."""

from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.database import engine

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health")
async def health():
    db_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "database": "up" if db_ok else "down",
        "mock_ai": settings.USE_MOCK_AI or not settings.OPENAI_API_KEY,
        "deployment_mode": settings.DEPLOYMENT_MODE,
        "billing_disabled": settings.billing_disabled,
        "providers": {
            "openai": bool(settings.OPENAI_API_KEY),
            "realesrgan": bool(settings.REALESRGAN_URL),
            "musicgen": bool(settings.REPLICATE_API_TOKEN),
            "elevenlabs": bool(settings.ELEVENLABS_API_KEY),
            "email": settings.EMAIL_PROVIDER,
        },
    }
