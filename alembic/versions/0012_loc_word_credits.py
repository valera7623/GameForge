"""Add localization_words_remaining on subscriptions."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_loc_word_credits"
down_revision: Union[str, None] = "0011_project_loc_glossary"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column(
            "localization_words_remaining",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "localization_words_remaining")
