"""Feedback inbox table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_feedback"
down_revision: Union[str, None] = "0012_loc_word_credits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    feedback_category = postgresql.ENUM(
        "bug", "idea", "billing", "other", name="FeedbackCategory", create_type=False
    )
    feedback_status = postgresql.ENUM(
        "new", "read", "closed", name="FeedbackStatus", create_type=False
    )
    op.execute("CREATE TYPE \"FeedbackCategory\" AS ENUM ('bug', 'idea', 'billing', 'other')")
    op.execute("CREATE TYPE \"FeedbackStatus\" AS ENUM ('new', 'read', 'closed')")

    op.create_table(
        "feedback_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("category", feedback_category, nullable=False),
        sa.Column("subject", sa.String(200), nullable=False, server_default=""),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("status", feedback_status, nullable=False, server_default="new"),
        sa.Column("page_url", sa.String(512), nullable=True),
        sa.Column("client_ip", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_feedback_messages_user_id", "feedback_messages", ["user_id"])
    op.create_index("ix_feedback_messages_status", "feedback_messages", ["status"])
    op.create_index("ix_feedback_messages_created_at", "feedback_messages", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_feedback_messages_created_at", table_name="feedback_messages")
    op.drop_index("ix_feedback_messages_status", table_name="feedback_messages")
    op.drop_index("ix_feedback_messages_user_id", table_name="feedback_messages")
    op.drop_table("feedback_messages")
    op.execute('DROP TYPE IF EXISTS "FeedbackStatus"')
    op.execute('DROP TYPE IF EXISTS "FeedbackCategory"')
