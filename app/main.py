"""AI Game Dev Toolkit — FastAPI application entrypoint."""

import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1 import (
    auth,
    billing,
    character_creator,
    dashboard,
    game_balancer,
    health,
    level_analyzer,
    level_designer,
    localization,
    orgs,
    playtest_analyzer,
    playtester,
    projects,
    quest_generator,
    sound_designer,
    store_description,
    texture_upscaler,
    trailer_script,
)
from app.api.v1 import content as public_content
from app.api.v1.admin import router as admin_router
from app.config import get_settings, validate_settings
from app.database import init_db
from app.middleware.api_request_log import ApiRequestLogMiddleware

settings = get_settings()
logger = logging.getLogger("gamedev")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        from app.core.logging_config import reset_request_id, set_request_id

        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        token = set_request_id(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            reset_request_id(token)


def _init_sentry() -> None:
    if not settings.SENTRY_DSN:
        return
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.APP_ENV,
        traces_sample_rate=0.1,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_settings(settings)

    from app.core.logging_config import configure_logging

    configure_logging()
    _init_sentry()

    await init_db()
    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.models.achievement import Achievement
    from app.services.generation_tracker import ACHIEVEMENT_THRESHOLDS

    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(Achievement).limit(1))
        if not existing.scalar_one_or_none():
            for code, name, desc, threshold, xp in ACHIEVEMENT_THRESHOLDS:
                session.add(
                    Achievement(
                        code=code,
                        name=name,
                        description=desc,
                        threshold=threshold,
                        xp_reward=xp,
                    )
                )
            await session.commit()
    yield


docs_url = None if settings.is_production else "/docs"
redoc_url = None if settings.is_production else "/redoc"
openapi_url = None if settings.is_production else "/openapi.json"

app = FastAPI(
    title=settings.APP_NAME,
    version="1.2.0",
    description="AI Game Dev Toolkit — 7 AI tools for game developers",
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(ApiRequestLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prefix = settings.API_V1_PREFIX
app.include_router(health.router, prefix=prefix)
app.include_router(auth.router, prefix=prefix)
app.include_router(projects.router, prefix=prefix)
app.include_router(orgs.router, prefix=prefix)
app.include_router(level_designer.router, prefix=prefix)
app.include_router(quest_generator.router, prefix=prefix)
app.include_router(texture_upscaler.router, prefix=prefix)
app.include_router(character_creator.router, prefix=prefix)
app.include_router(sound_designer.router, prefix=prefix)
app.include_router(playtester.router, prefix=prefix)
app.include_router(localization.router, prefix=prefix)
app.include_router(game_balancer.router, prefix=prefix)
app.include_router(level_analyzer.router, prefix=prefix)
app.include_router(store_description.router, prefix=prefix)
app.include_router(playtest_analyzer.router, prefix=prefix)
app.include_router(trailer_script.router, prefix=prefix)
app.include_router(billing.router, prefix=prefix)
app.include_router(dashboard.router, prefix=prefix)
app.include_router(admin_router, prefix=prefix)
app.include_router(public_content.router, prefix=prefix)

local_assets = Path("/tmp/gamedev-assets")
local_assets.mkdir(parents=True, exist_ok=True)


@app.get("/local-assets/{asset_path:path}")
async def serve_local_asset(asset_path: str, request: Request, sig: str = ""):
    """Serve local fallback assets only with a valid HMAC signature."""
    from app.services.storage import verify_local_asset_sig

    if not verify_local_asset_sig(asset_path, sig):
        raise HTTPException(status_code=403, detail="Invalid or missing signature")
    path = local_assets / asset_path
    if not path.is_file() or not str(path.resolve()).startswith(str(local_assets.resolve())):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path)


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "health": f"{prefix}/health",
        "version": "1.2.0",
    }
