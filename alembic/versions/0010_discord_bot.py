"""Add discord_bot tool + Discord bot tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_discord_bot"
down_revision: Union[str, None] = "0009_review_analyzer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE \"ToolType\" ADD VALUE IF NOT EXISTS 'discord_bot'")

    op.create_table(
        "discord_bot_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bot_name", sa.String(120), nullable=False, server_default="GameForge Bot"),
        sa.Column("guild_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("channel_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("bot_token_enc", sa.Text(), nullable=True),
        sa.Column("token_last4", sa.String(8), nullable=True),
        sa.Column("prefix", sa.String(8), nullable=False, server_default="!"),
        sa.Column("moderation_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("welcome_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("analytics_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("moderation", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("welcome", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("analytics", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("game_info", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_connected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("stats", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_discord_bot_configs_user_id", "discord_bot_configs", ["user_id"])

    op.create_table(
        "discord_bot_commands",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("config_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("discord_bot_configs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("command", sa.String(64), nullable=False),
        sa.Column("description", sa.String(300), nullable=False, server_default=""),
        sa.Column("usage", sa.String(120), nullable=False, server_default=""),
        sa.Column("response", sa.Text(), nullable=False, server_default=""),
        sa.Column("category", sa.String(32), nullable=False, server_default="custom"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("config_id", "command", name="uq_discord_cmd_config_command"),
    )
    op.create_index("ix_discord_bot_commands_config_id", "discord_bot_commands", ["config_id"])

    op.create_table(
        "discord_bot_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("config_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("discord_bot_configs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("guild_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("channel_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("discord_user_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_moderated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("moderated_by", sa.String(32), nullable=True),
        sa.Column("moderation_action", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_discord_bot_messages_config_id", "discord_bot_messages", ["config_id"])

    op.create_table(
        "discord_bot_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("config_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("discord_bot_configs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("guild_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("discord_user_id", sa.String(64), nullable=False),
        sa.Column("username", sa.String(120), nullable=False, server_default=""),
        sa.Column("display_name", sa.String(120), nullable=False, server_default=""),
        sa.Column("roles", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("messages_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warnings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_banned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("config_id", "discord_user_id", name="uq_discord_user_config"),
    )
    op.create_index("ix_discord_bot_users_config_id", "discord_bot_users", ["config_id"])


def downgrade() -> None:
    op.drop_table("discord_bot_users")
    op.drop_table("discord_bot_messages")
    op.drop_table("discord_bot_commands")
    op.drop_table("discord_bot_configs")
