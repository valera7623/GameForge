"""Shared tool execution helper — quota reserve, fail/refund, response mapping."""

from __future__ import annotations

import logging
import time
from typing import Any, Awaitable, Callable, Optional
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limiter import _client_ip, rate_limit
from app.deps import refund_generation_quota, reserve_generation_quota
from app.models.generation import Generation, ToolType
from app.models.user import User
from app.schemas import GenerationResponse
from app.services.generation_tracker import complete_generation, create_generation, fail_generation
from app.services.openai_client import begin_llm_usage, get_llm_usage, reset_llm_usage
from app.services.ops_logs import record_error
from app.services.platform_settings import get_ai_models_settings, is_tool_enabled

logger = logging.getLogger(__name__)

AsyncToolFn = Callable[[], Awaitable[dict[str, Any]]]


async def _ensure_tool_enabled(db: AsyncSession, tool: ToolType) -> None:
    if not await is_tool_enabled(db, tool):
        raise HTTPException(
            status_code=503,
            detail=f"Tool '{tool.value}' is temporarily disabled by an administrator.",
        )


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
    await _ensure_tool_enabled(db, tool)
    await reserve_generation_quota(user, db)

    gen = await create_generation(
        db,
        user,
        tool,
        input_data,
        project_id=project_id,
        title=title,
        client_ip=_client_ip(request),
    )
    begin_llm_usage()
    t0 = time.perf_counter()
    try:
        output = await run()
        duration_ms = int((time.perf_counter() - t0) * 1000)
        urls = asset_urls_from(output) if asset_urls_from else None
        pricing = await get_ai_models_settings(db)
        gen = await complete_generation(
            db,
            gen,
            user,
            output,
            asset_urls=urls,
            duration_ms=duration_ms,
            usage=get_llm_usage(),
            pricing=pricing,
        )
    except Exception as exc:
        duration_ms = int((time.perf_counter() - t0) * 1000)
        logger.exception("Tool %s failed for user %s", tool.value, user.id)
        await fail_generation(db, gen, str(exc), duration_ms=duration_ms)
        await record_error(
            db,
            source="generation",
            message=str(exc),
            status_code=502,
            path=str(request.url.path),
            user_id=user.id,
            generation_id=gen.id,
            request_id=getattr(request.state, "request_id", None),
        )
        await refund_generation_quota(user, db)
        await db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        reset_llm_usage()

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
    await _ensure_tool_enabled(db, tool)
    await reserve_generation_quota(user, db)
    gen = await create_generation(
        db,
        user,
        tool,
        input_data,
        project_id=project_id,
        title=title,
        client_ip=_client_ip(request),
    )
    try:
        enqueue(gen)
        await db.flush()
    except Exception as exc:
        logger.exception("Failed to enqueue %s", tool.value)
        await fail_generation(db, gen, str(exc))
        await record_error(
            db,
            source="generation",
            message=str(exc),
            status_code=502,
            path=str(request.url.path),
            user_id=user.id,
            generation_id=gen.id,
            request_id=getattr(request.state, "request_id", None),
        )
        await refund_generation_quota(user, db)
        await db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(gen)
    return generation_to_response(gen)
