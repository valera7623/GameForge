"""Middleware: brief API request logging (no bodies) + 5xx error logs."""

from __future__ import annotations

import logging
import time
from typing import Optional
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.rate_limiter import _client_ip

logger = logging.getLogger(__name__)

SKIP_PREFIXES = ("/health", "/docs", "/redoc", "/openapi", "/local-assets")


class ApiRequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        # Only /api/v1/*
        if "/api/v1" not in path:
            return await call_next(request)
        api_path = path
        if any(api_path.endswith(s) or f"/api/v1{s}" in api_path or api_path.endswith("/health") for s in ("/health",)):
            if api_path.rstrip("/").endswith("/health"):
                return await call_next(request)

        t0 = time.perf_counter()
        response: Optional[Response] = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = int((time.perf_counter() - t0) * 1000)
            status_code = response.status_code if response is not None else 500
            try:
                # Global AsyncSessionLocal is bound to the app engine loop; pytest-asyncio
                # uses a fresh loop per test — skip persist to avoid MissingGreenlet.
                from app.config import get_settings

                if get_settings().APP_ENV.lower() != "test":
                    await _persist_log(request, api_path, status_code, duration_ms)
            except Exception:
                logger.exception("Failed to persist API request log")


async def _persist_log(request: Request, path: str, status_code: int, duration_ms: int) -> None:
    from app.database import AsyncSessionLocal
    from app.services.ops_logs import record_api_request, record_error

    user_id = None
    # Best-effort: decode cookie without hard dependency if missing
    try:
        from app.config import get_settings
        from app.core.security import decode_token

        cfg = get_settings()
        token = request.cookies.get(cfg.ACCESS_COOKIE)
        if not token:
            auth = request.headers.get("Authorization") or ""
            if auth.lower().startswith("bearer "):
                token = auth[7:].strip()
        if token:
            payload = decode_token(token)
            if payload and payload.get("type") == "access" and payload.get("sub"):
                user_id = UUID(str(payload["sub"]))
    except Exception:
        user_id = None

    request_id = getattr(request.state, "request_id", None)
    ip = _client_ip(request)

    async with AsyncSessionLocal() as session:
        await record_api_request(
            session,
            method=request.method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            user_id=user_id,
            ip=ip,
            request_id=request_id,
        )
        if status_code >= 500:
            await record_error(
                session,
                source="api",
                message=f"{request.method} {path} → {status_code}",
                status_code=status_code,
                path=path,
                user_id=user_id,
                request_id=request_id,
            )
        await session.commit()
