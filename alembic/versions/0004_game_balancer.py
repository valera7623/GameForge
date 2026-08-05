"""Add ToolType.game_balancer enum value."""

from typing import Sequence, Union

from alembic import op

revision: str = "0004_game_balancer"
down_revision: Union[str, None] = "0003_admin_upgrade"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE \"ToolType\" ADD VALUE IF NOT EXISTS 'game_balancer'")


def downgrade() -> None:
    # PostgreSQL cannot easily remove enum values; leave in place.
    pass
