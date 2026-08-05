"""Add ToolType.trailer_script enum value."""

from typing import Sequence, Union

from alembic import op

revision: str = "0008_trailer_script"
down_revision: Union[str, None] = "0007_playtest_analyzer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE \"ToolType\" ADD VALUE IF NOT EXISTS 'trailer_script'")


def downgrade() -> None:
    pass
