"""Add analysis detail fields

Adds posture/technique scores, error counters, processing time,
raw AI response, and failure message to analyses.

Revision ID: 0002_analysis_details
Revises: 0001_initial
Create Date: 2026-10-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002_analysis_details"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("analyses", sa.Column("posture_score", sa.Float(), nullable=True))
    op.add_column("analyses", sa.Column("technique_score", sa.Float(), nullable=True))
    op.add_column(
        "analyses",
        sa.Column("total_errors", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column("analyses", sa.Column("processing_time", sa.Float(), nullable=True))
    op.add_column("analyses", sa.Column("ai_response", sa.Text(), nullable=True))
    op.add_column("analyses", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("analyses", "error_message")
    op.drop_column("analyses", "ai_response")
    op.drop_column("analyses", "processing_time")
    op.drop_column("analyses", "total_errors")
    op.drop_column("analyses", "technique_score")
    op.drop_column("analyses", "posture_score")
