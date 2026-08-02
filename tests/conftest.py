"""Pytest configuration and fixtures."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Test env before app imports
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-use")
os.environ.setdefault("ALLOW_MOCK_BILLING", "true")
os.environ.setdefault("USE_MOCK_AI", "true")
os.environ.setdefault("FORCE_PLAN", "studio")
os.environ.setdefault("CORS_ORIGINS", "http://testserver")
os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get("TEST_DATABASE_URL", "postgresql+asyncpg://gamedev:gamedev@localhost:5432/gamedev_test"),
)
os.environ.setdefault(
    "DATABASE_URL_SYNC",
    os.environ.get("TEST_DATABASE_URL_SYNC", "postgresql://gamedev:gamedev@localhost:5432/gamedev_test"),
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models import *  # noqa: F401,F403

get_settings.cache_clear()
settings = get_settings()


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(engine) -> AsyncGenerator[AsyncClient, None]:
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()
