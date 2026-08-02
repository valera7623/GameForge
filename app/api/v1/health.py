"""Health / readiness checks."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.database import engine

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health")
async def health():
    payload = {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "deployment_mode": settings.DEPLOYMENT_MODE,
    }
    if not settings.is_production:
        payload.update(
            {
                "mock_ai": settings.USE_MOCK_AI or not settings.OPENAI_API_KEY,
                "billing_disabled": settings.billing_disabled,
                "providers": {
                    "openai": bool(settings.OPENAI_API_KEY),
                    "realesrgan": bool(settings.REALESRGAN_URL),
                    "musicgen": bool(settings.REPLICATE_API_TOKEN),
                    "elevenlabs": bool(settings.ELEVENLABS_API_KEY),
                    "email": settings.EMAIL_PROVIDER,
                },
            }
        )
    return payload


@router.get("/health/ready")
async def readiness():
    checks = {"database": False, "redis": False}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            checks["database"] = True
    except Exception:
        checks["database"] = False

    try:
        import redis

        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
        checks["redis"] = bool(r.ping())
    except Exception:
        checks["redis"] = False

    # Broker is Redis DB — same host ping is enough for readiness
    checks["broker"] = checks["redis"]
    ok = all(checks.values())
    body = {"status": "ok" if ok else "degraded", "checks": checks}
    if not ok:
        return JSONResponse(status_code=503, content=body)
    return body
