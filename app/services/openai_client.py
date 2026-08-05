"""LLM usage accumulator + OpenAI helpers."""

from __future__ import annotations

import contextvars
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Optional

import httpx
from openai import AsyncOpenAI

from app.config import get_settings

_usage_var: contextvars.ContextVar[Optional["LlmUsage"]] = contextvars.ContextVar("llm_usage", default=None)


@dataclass
class LlmUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model_name: Optional[str] = None
    cost_key: str = "openai_chat"
    image_count: int = 0
    per_call_keys: list[str] = field(default_factory=list)

    def add_chat(self, *, prompt: int, completion: int, model: Optional[str]) -> None:
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        if model:
            self.model_name = model
        self.cost_key = "openai_chat"

    def add_image(self, *, model: Optional[str], count: int = 1) -> None:
        self.image_count += count
        if model:
            self.model_name = model
        self.cost_key = "openai_image"

    def add_provider(self, cost_key: str, model: Optional[str] = None) -> None:
        self.per_call_keys.append(cost_key)
        if model:
            self.model_name = model


def begin_llm_usage() -> LlmUsage:
    usage = LlmUsage()
    _usage_var.set(usage)
    return usage


def get_llm_usage() -> Optional[LlmUsage]:
    return _usage_var.get()


def reset_llm_usage() -> None:
    _usage_var.set(None)


@lru_cache
def get_openai_client() -> AsyncOpenAI:
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


async def chat_completion(**kwargs: Any) -> Any:
    """chat.completions.create that records token usage into the active context."""
    client = get_openai_client()
    resp = await client.chat.completions.create(**kwargs)
    usage = get_llm_usage()
    if usage is not None and getattr(resp, "usage", None):
        usage.add_chat(
            prompt=int(resp.usage.prompt_tokens or 0),
            completion=int(resp.usage.completion_tokens or 0),
            model=getattr(resp, "model", None) or kwargs.get("model"),
        )
    elif usage is not None:
        usage.model_name = usage.model_name or kwargs.get("model")
        usage.cost_key = "openai_chat"
    return resp


async def image_generate(**kwargs: Any) -> Any:
    client = get_openai_client()
    resp = await client.images.generate(**kwargs)
    usage = get_llm_usage()
    if usage is not None:
        n = int(kwargs.get("n") or 1)
        usage.add_image(model=kwargs.get("model"), count=n)
    return resp


def record_provider_call(cost_key: str, model: Optional[str] = None) -> None:
    usage = get_llm_usage()
    if usage is not None:
        usage.add_provider(cost_key, model)
