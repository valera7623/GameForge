"""Add ToolType.level_analyzer enum value."""

from typing import Sequence, Union

from alembic import op

revision: str = "0005_level_analyzer"
down_revision: Union[str, None] = "0004_game_balancer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE \"ToolType\" ADD VALUE IF NOT EXISTS 'level_analyzer'")


def downgrade() -> None:
    pass
