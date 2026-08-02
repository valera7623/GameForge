"""AI Game Dev Toolkit — FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import (
    auth,
    billing,
    character_creator,
    dashboard,
    health,
    level_designer,
    localization,
    orgs,
    playtester,
    projects,
    quest_generator,
    sound_designer,
    texture_upscaler,
)
from app.config import get_settings
from app.database import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
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


app = FastAPI(
    title=settings.APP_NAME,
    version="1.1.0",
    description="AI Game Dev Toolkit — 7 AI tools for game developers",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list + ["*"],
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
app.include_router(billing.router, prefix=prefix)
app.include_router(dashboard.router, prefix=prefix)

# Local asset fallback
local_assets = Path("/tmp/gamedev-assets")
local_assets.mkdir(parents=True, exist_ok=True)
app.mount("/local-assets", StaticFiles(directory=str(local_assets)), name="local-assets")


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "docs": "/docs",
        "health": f"{prefix}/health",
        "version": "1.0.0",
    }
