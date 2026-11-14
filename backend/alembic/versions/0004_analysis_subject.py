"""Add who is analyzed and which partner an error belongs to

Revision ID: 0004_analysis_subject
Revises: 0003_user_display_name
Create Date: 2026-11-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_analysis_subject"
down_revision: Union[str, None] = "0003_user_display_name"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column("subject", sa.String(length=16), nullable=False, server_default=sa.text("'both'")),
    )
    op.add_column(
        "errors",
        sa.Column("person", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("errors", "person")
    op.drop_column("analyses", "subject")
