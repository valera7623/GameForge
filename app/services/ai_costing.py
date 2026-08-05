"""Estimate AI generation cost from usage + platform pricing."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from app.models.platform_setting import DEFAULT_AI_MODELS
from app.services.openai_client import LlmUsage

ZERO = Decimal("0")


def merge_ai_models(raw: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    out = {k: dict(v) for k, v in DEFAULT_AI_MODELS.items()}
    if raw:
        for key, val in raw.items():
            if isinstance(val, dict):
                base = out.get(key, {})
                merged = dict(base)
                merged.update(val)
                out[key] = merged
    return out


def estimate_cost_usd(usage: LlmUsage, pricing: Optional[dict[str, Any]] = None) -> Decimal:
    prices = merge_ai_models(pricing)
    total = ZERO

    if usage.prompt_tokens or usage.completion_tokens:
        chat = prices.get("openai_chat") or {}
        inp = Decimal(str(chat.get("input_per_1m", 0)))
        outp = Decimal(str(chat.get("output_per_1m", 0)))
        total += (Decimal(usage.prompt_tokens) / Decimal(1_000_000)) * inp
        total += (Decimal(usage.completion_tokens) / Decimal(1_000_000)) * outp

    if usage.image_count:
        img = prices.get("openai_image") or {}
        per = Decimal(str(img.get("per_image", 0)))
        total += per * Decimal(usage.image_count)

    for key in usage.per_call_keys:
        entry = prices.get(key) or {}
        total += Decimal(str(entry.get("per_call", 0)))

    return total.quantize(Decimal("0.000001"))
