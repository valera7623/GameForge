"""Shared OpenAI client — ProxyAPI-compatible by default."""

from functools import lru_cache

import httpx
from openai import AsyncOpenAI

from app.config import get_settings


@lru_cache
def get_openai_client() -> AsyncOpenAI:
    """
    OpenAI SDK pointed at ProxyAPI (or any OpenAI-compatible gateway).

    Set OPENAI_API_KEY to your ProxyAPI key and keep:
      OPENAI_BASE_URL=https://api.proxyapi.ru/openai/v1
    """
    settings = get_settings()
    timeout = httpx.Timeout(settings.OPENAI_TIMEOUT_SEC, connect=10.0)
    return AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        timeout=timeout,
        max_retries=2,
    )


def openai_enabled() -> bool:
    settings = get_settings()
    return bool(settings.OPENAI_API_KEY) and not settings.USE_MOCK_AI
