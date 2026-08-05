"""Add ToolType.playtest_analyzer enum value."""

from typing import Sequence, Union

from alembic import op

revision: str = "0007_playtest_analyzer"
down_revision: Union[str, None] = "0006_store_description"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE \"ToolType\" ADD VALUE IF NOT EXISTS 'playtest_analyzer'")


def downgrade() -> None:
    pass
