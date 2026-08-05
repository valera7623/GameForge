"""Load / save platform settings (tools toggles, general)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.generation import ToolType
from app.models.platform_setting import (
    DEFAULT_GENERAL,
    DEFAULT_TOOLS,
    SETTING_GENERAL,
    SETTING_TOOLS,
    PlatformSetting,
)


async def get_setting(db: AsyncSession, key: str, default: dict[str, Any]) -> dict[str, Any]:
    result = await db.execute(select(PlatformSetting).where(PlatformSetting.key == key))
    row = result.scalar_one_or_none()
    if not row:
        return dict(default)
    value = row.value or {}
    # Merge defaults so new tools appear enabled
    merged = dict(default)
    merged.update(value)
    return merged


async def set_setting(db: AsyncSession, key: str, value: dict[str, Any]) -> dict[str, Any]:
    result = await db.execute(select(PlatformSetting).where(PlatformSetting.key == key))
    row = result.scalar_one_or_none()
    if not row:
        row = PlatformSetting(key=key, value=value)
        db.add(row)
    else:
        row.value = value
    await db.flush()
    return row.value


async def get_general_settings(db: AsyncSession) -> dict[str, Any]:
    return await get_setting(db, SETTING_GENERAL, DEFAULT_GENERAL)


async def get_tools_settings(db: AsyncSession) -> dict[str, Any]:
    raw = await get_setting(db, SETTING_TOOLS, DEFAULT_TOOLS)
    # Normalize structure
    out: dict[str, Any] = {}
    for name, default in DEFAULT_TOOLS.items():
        entry = raw.get(name) or {}
        out[name] = {
            "enabled": bool(entry.get("enabled", default.get("enabled", True))),
            "display_name": entry.get("display_name") or default.get("display_name") or name,
        }
    return out


async def is_tool_enabled(db: AsyncSession, tool: ToolType | str) -> bool:
    name = tool.value if isinstance(tool, ToolType) else tool
    tools = await get_tools_settings(db)
    entry = tools.get(name) or {"enabled": True}
    return bool(entry.get("enabled", True))
