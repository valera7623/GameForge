"""Discord bot configuration and community tooling models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DiscordBotConfig(Base):
    __tablename__ = "discord_bot_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    bot_name: Mapped[str] = mapped_column(String(120), nullable=False, default="GameForge Bot")
    guild_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    channel_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    # Fernet ciphertext; never return raw token in API responses.
    bot_token_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_last4: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    prefix: Mapped[str] = mapped_column(String(8), nullable=False, default="!")
    moderation_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    welcome_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    analytics_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    moderation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    welcome: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    analytics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    game_info: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    stats: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DiscordBotCommand(Base):
    __tablename__ = "discord_bot_commands"
    __table_args__ = (UniqueConstraint("config_id", "command", name="uq_discord_cmd_config_command"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discord_bot_configs.id", ondelete="CASCADE"), index=True
    )
    command: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    usage: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    response: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="custom")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DiscordBotMessage(Base):
    """Optional moderation / ingest log for sample or live messages."""

    __tablename__ = "discord_bot_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discord_bot_configs.id", ondelete="CASCADE"), index=True
    )
    guild_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    channel_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    discord_user_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_moderated: Mapped[bool] = mapped_column(Boolean, default=False)
    moderated_by: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    moderation_action: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DiscordBotUser(Base):
    __tablename__ = "discord_bot_users"
    __table_args__ = (UniqueConstraint("config_id", "discord_user_id", name="uq_discord_user_config"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discord_bot_configs.id", ondelete="CASCADE"), index=True
    )
    guild_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    discord_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    username: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    display_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    roles: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    messages_count: Mapped[int] = mapped_column(Integer, default=0)
    warnings_count: Mapped[int] = mapped_column(Integer, default=0)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
