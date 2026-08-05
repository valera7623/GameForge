"""Platform-wide key/value settings (admin-editable)."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Setting keys
SETTING_GENERAL = "general"
SETTING_TOOLS = "tools"
SETTING_AI_MODELS = "ai_models"

DEFAULT_GENERAL = {
    "app_name": "GameForge",
    "domain": "gameforge.website",
    "notes": "",
}

DEFAULT_TOOLS = {
    "level_designer": {"enabled": True, "display_name": "Level Designer"},
    "quest_generator": {"enabled": True, "display_name": "Quest Generator"},
    "texture_upscaler": {"enabled": True, "display_name": "Texture Upscaler"},
    "character_creator": {"enabled": True, "display_name": "Character Creator"},
    "sound_designer": {"enabled": True, "display_name": "Sound Designer"},
    "playtester": {"enabled": True, "display_name": "Playtester"},
    "localization": {"enabled": True, "display_name": "Localization"},
    "game_balancer": {"enabled": True, "display_name": "Game Balancer"},
    "level_analyzer": {"enabled": True, "display_name": "Level Analyzer"},
    "store_description": {"enabled": True, "display_name": "Store Description"},
    "playtest_analyzer": {"enabled": True, "display_name": "AI Playtest Analyzer"},
}

DEFAULT_AI_MODELS = {
    "openai_chat": {"model": "gpt-4o-mini", "input_per_1m": 0.15, "output_per_1m": 0.60},
    "openai_image": {"model": "dall-e-3", "per_image": 0.04},
    "stability_audio": {"per_call": 0.02},
    "replicate_musicgen": {"per_call": 0.01},
    "elevenlabs": {"per_call": 0.03},
    "stability_image": {"per_call": 0.02},
    "realesrgan": {"per_call": 0.005},
}


class PlatformSetting(Base):
    __tablename__ = "platform_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
