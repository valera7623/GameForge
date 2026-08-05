"""Add ToolType.review_analyzer enum value."""

from typing import Sequence, Union

from alembic import op

revision: str = "0009_review_analyzer"
down_revision: Union[str, None] = "0008_trailer_script"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE \"ToolType\" ADD VALUE IF NOT EXISTS 'review_analyzer'")


def downgrade() -> None:
    pass
