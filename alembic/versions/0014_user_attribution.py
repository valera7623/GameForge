"""User signup attribution for LocForge / UTM."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_user_attribution"
down_revision: Union[str, None] = "0013_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("signup_source", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("signup_pack", sa.String(length=32), nullable=True))
    op.add_column(
        "users",
        sa.Column("attribution", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("first_localize_notified", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("users", "first_localize_notified")
    op.drop_column("users", "attribution")
    op.drop_column("users", "signup_pack")
    op.drop_column("users", "signup_source")
