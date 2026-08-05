"""Add ToolType.store_description enum value."""

from typing import Sequence, Union

from alembic import op

revision: str = "0006_store_description"
down_revision: Union[str, None] = "0005_level_analyzer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE \"ToolType\" ADD VALUE IF NOT EXISTS 'store_description'")


def downgrade() -> None:
    pass
