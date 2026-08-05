"""Admin panel: staff roles, last_login_at, platform_settings."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_admin_panel"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Expand UserRole enum (PostgreSQL)
    op.execute("ALTER TYPE \"UserRole\" ADD VALUE IF NOT EXISTS 'super_admin'")
    op.execute("ALTER TYPE \"UserRole\" ADD VALUE IF NOT EXISTS 'manager'")
    op.execute("ALTER TYPE \"UserRole\" ADD VALUE IF NOT EXISTS 'support'")

    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "platform_settings",
        sa.Column("key", sa.String(length=64), primary_key=True),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("platform_settings")
    op.drop_column("users", "last_login_at")
    # Enum values cannot be removed safely in PostgreSQL — leave them.
