"""Shared tool execution helper — quota reserve, fail/refund, response mapping."""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Optional
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limiter import rate_limit
from app.deps import refund_generation_quota, reserve_generation_quota
from app.models.generation import Generation, ToolType
from app.models.user import User
from app.schemas import GenerationResponse
from app.services.generation_tracker import complete_generation, create_generation, fail_generation

logger = logging.getLogger(__name__)

AsyncToolFn = Callable[[], Awaitable[dict[str, Any]]]


def generation_to_response(gen: Generation) -> GenerationResponse:
    return GenerationResponse(
        id=gen.id,
        tool=gen.tool.value,
        status=gen.status.value,
        title=gen.title,
        input_data=gen.input_data,
        output_data=gen.output_data,
        asset_urls=gen.asset_urls,
        error_message=gen.error_message,
        xp_awarded=gen.xp_awarded,
        project_id=gen.project_id,
        created_at=gen.created_at,
        completed_at=gen.completed_at,
    )


async def run_tool(
    *,
    request: Request,
    db: AsyncSession,
    user: User,
    tool: ToolType,
    input_data: dict[str, Any],
    title: Optional[str],
    project_id: Optional[UUID],
    run: AsyncToolFn,
    asset_urls_from: Optional[Callable[[dict[str, Any]], Optional[list]]] = None,
) -> GenerationResponse:
    await rate_limit(request)
    await reserve_generation_quota(user, db)

    gen = await create_generation(
        db,
        user,
        tool,
        input_data,
        project_id=project_id,
        title=title,
    )
    try:
        output = await run()
        urls = asset_urls_from(output) if asset_urls_from else None
        gen = await complete_generation(db, gen, user, output, asset_urls=urls)
    except Exception as exc:
        logger.exception("Tool %s failed for user %s", tool.value, user.id)
        await fail_generation(db, gen, str(exc))
        await refund_generation_quota(user, db)
        await db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return generation_to_response(gen)


async def enqueue_tool(
    *,
    request: Request,
    db: AsyncSession,
    user: User,
    tool: ToolType,
    input_data: dict[str, Any],
    title: Optional[str],
    project_id: Optional[UUID],
    enqueue: Callable[[Generation], None],
) -> GenerationResponse:
    """Reserve quota, create generation, hand off to Celery."""
    await rate_limit(request)
    await reserve_generation_quota(user, db)
    gen = await create_generation(
        db,
        user,
        tool,
        input_data,
        project_id=project_id,
        title=title,
    )
    try:
        enqueue(gen)
        await db.flush()
    except Exception as exc:
        logger.exception("Failed to enqueue %s", tool.value)
        await fail_generation(db, gen, str(exc))
        await refund_generation_quota(user, db)
        await db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(gen)
    return generation_to_response(gen)
