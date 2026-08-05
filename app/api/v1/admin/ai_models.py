"""Admin AI models pricing + cost aggregates."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Date

from app.api.v1.admin.schemas import AiCostsOut, AiModelsOut, AiModelsUpdate
from app.core.rbac import require_permission
from app.database import get_db
from app.models.generation import Generation
from app.models.platform_setting import SETTING_AI_MODELS
from app.models.user import User
from app.services.ops_logs import record_audit
from app.services.platform_settings import get_ai_models_settings, set_setting

router = APIRouter()


@router.get("/ai-models", response_model=AiModelsOut)
async def get_ai_models(
    user: User = Depends(require_permission("dashboard:read")),
    db: AsyncSession = Depends(get_db),
):
    return AiModelsOut(models=await get_ai_models_settings(db))


@router.put("/ai-models", response_model=AiModelsOut)
async def put_ai_models(
    body: AiModelsUpdate,
    user: User = Depends(require_permission("settings:write")),
    db: AsyncSession = Depends(get_db),
):
    saved = await set_setting(db, SETTING_AI_MODELS, body.models)
    await record_audit(
        db,
        actor_id=user.id,
        action="ai_models.update",
        target_type="platform_setting",
        target_id=SETTING_AI_MODELS,
        meta={"keys": list(body.models.keys())},
    )
    from app.services.ai_costing import merge_ai_models

    return AiModelsOut(models=merge_ai_models(saved))


@router.get("/ai-models/costs", response_model=AiCostsOut)
async def ai_costs(
    days: int = Query(30, ge=1, le=365),
    date_from: Optional[datetime] = Query(None, alias="from"),
    date_to: Optional[datetime] = Query(None, alias="to"),
    user: User = Depends(require_permission("dashboard:read")),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    start = date_from or (now - timedelta(days=days))
    end = date_to or now

    total_q = await db.execute(
        select(func.coalesce(func.sum(Generation.cost_usd), 0)).where(
            Generation.created_at >= start,
            Generation.created_at <= end,
        )
    )
    total = float(total_q.scalar() or 0)

    by_tool_rows = await db.execute(
        select(Generation.tool, func.coalesce(func.sum(Generation.cost_usd), 0), func.count())
        .where(Generation.created_at >= start, Generation.created_at <= end)
        .group_by(Generation.tool)
    )
    by_tool = [
        {"tool": t.value if hasattr(t, "value") else str(t), "cost_usd": float(c), "count": n}
        for t, c, n in by_tool_rows.all()
    ]

    by_day_rows = await db.execute(
        select(cast(Generation.created_at, Date), func.coalesce(func.sum(Generation.cost_usd), 0))
        .where(Generation.created_at >= start, Generation.created_at <= end)
        .group_by(cast(Generation.created_at, Date))
        .order_by(cast(Generation.created_at, Date))
    )
    by_day = [{"date": str(d), "cost_usd": float(c)} for d, c in by_day_rows.all()]

    by_model_rows = await db.execute(
        select(
            func.coalesce(Generation.model_name, "unknown"),
            func.coalesce(func.sum(Generation.cost_usd), 0),
            func.count(),
        )
        .where(Generation.created_at >= start, Generation.created_at <= end)
        .group_by(func.coalesce(Generation.model_name, "unknown"))
    )
    by_model = [{"model": m, "cost_usd": float(c), "count": n} for m, c, n in by_model_rows.all()]

    return AiCostsOut(total_usd=total, by_tool=by_tool, by_day=by_day, by_model=by_model)
