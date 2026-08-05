"""Admin upgrade: generation metrics, ops logs, content CMS."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_admin_upgrade"
down_revision: Union[str, None] = "0002_admin_panel"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("generations", sa.Column("client_ip", sa.String(length=64), nullable=True))
    op.add_column("generations", sa.Column("duration_ms", sa.Integer(), nullable=True))
    op.add_column("generations", sa.Column("prompt_tokens", sa.Integer(), nullable=True))
    op.add_column("generations", sa.Column("completion_tokens", sa.Integer(), nullable=True))
    op.add_column("generations", sa.Column("cost_usd", sa.Numeric(12, 6), nullable=True))
    op.add_column("generations", sa.Column("model_name", sa.String(length=128), nullable=True))

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])

    op.create_table(
        "error_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("path", sa.String(length=512), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("generation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("generations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_error_logs_created_at", "error_logs", ["created_at"])

    op.create_table(
        "api_request_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_api_request_logs_created_at", "api_request_logs", ["created_at"])
    op.create_index("ix_api_request_logs_path", "api_request_logs", ["path"])

    op.create_table(
        "content_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False, server_default="en"),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body_md", sa.Text(), nullable=False, server_default=""),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("meta_title", sa.String(length=500), nullable=True),
        sa.Column("meta_description", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("kind", "slug", "locale", name="uq_content_kind_slug_locale"),
    )
    op.create_index("ix_content_items_kind_status", "content_items", ["kind", "status"])


def downgrade() -> None:
    op.drop_table("content_items")
    op.drop_table("api_request_logs")
    op.drop_table("error_logs")
    op.drop_table("audit_logs")
    op.drop_column("generations", "model_name")
    op.drop_column("generations", "cost_usd")
    op.drop_column("generations", "completion_tokens")
    op.drop_column("generations", "prompt_tokens")
    op.drop_column("generations", "duration_ms")
    op.drop_column("generations", "client_ip")
