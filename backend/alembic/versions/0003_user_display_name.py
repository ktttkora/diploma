"""Add optional display name to users

Revision ID: 0003_user_display_name
Revises: 0002_analysis_details
Create Date: 2026-11-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_user_display_name"
down_revision: Union[str, None] = "0002_analysis_details"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "display_name")
