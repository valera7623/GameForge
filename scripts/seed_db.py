"""Seed achievements, demo user, and sample project."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure /app on path when run inside container
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.config import get_settings
from app.core.security import hash_password
from app.database import AsyncSessionLocal, init_db
from app.models.achievement import Achievement
from app.models.project import GameEngine, Project
from app.models.subscription import PlanType, Subscription, SubscriptionStatus
from app.models.user import User, UserRole
from app.services.generation_tracker import ACHIEVEMENT_THRESHOLDS

settings = get_settings()


async def main() -> None:
    await init_db()
    async with AsyncSessionLocal() as db:
        # Achievements
        for code, name, desc, threshold, xp in ACHIEVEMENT_THRESHOLDS:
            exists = await db.execute(select(Achievement).where(Achievement.code == code))
            if not exists.scalar_one_or_none():
                db.add(
                    Achievement(
                        code=code,
                        name=name,
                        description=desc,
                        threshold=threshold,
                        xp_reward=xp,
                    )
                )

        # Demo user
        email = "demo@gamedev.ai"
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email=email,
                hashed_password=hash_password("demo123456"),
                full_name="Demo Developer",
                role=UserRole.USER,
                is_verified=True,
                xp=0,
                generation_reset_at=datetime.now(timezone.utc),
            )
            db.add(user)
            await db.flush()
            db.add(
                Subscription(
                    user_id=user.id,
                    plan=PlanType.INDIE,
                    status=SubscriptionStatus.ACTIVE,
                    generations_limit=settings.INDIE_GENERATIONS,
                    current_period_start=datetime.now(timezone.utc),
                    current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
                )
            )
            db.add(
                Project(
                    owner_id=user.id,
                    name="Dungeon Explorer",
                    description="Sample Unreal project for the GameForge demo",
                    engine=GameEngine.UNREAL,
                )
            )
            print(f"Created demo user: {email} / demo123456")
        else:
            print(f"Demo user already exists: {email}")

        # Admin
        admin_email = "admin@gamedev.ai"
        result = await db.execute(select(User).where(User.email == admin_email))
        if not result.scalar_one_or_none():
            admin = User(
                email=admin_email,
                hashed_password=hash_password("admin123456"),
                full_name="Admin",
                role=UserRole.ADMIN,
                is_verified=True,
                generation_reset_at=datetime.now(timezone.utc),
            )
            db.add(admin)
            await db.flush()
            db.add(
                Subscription(
                    user_id=admin.id,
                    plan=PlanType.ENTERPRISE,
                    status=SubscriptionStatus.ACTIVE,
                    generations_limit=999999,
                )
            )
            print(f"Created admin: {admin_email} / admin123456")

        await db.commit()
        print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
