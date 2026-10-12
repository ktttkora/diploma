"""Initial migration: users, videos, analyses, errors, temp_uploads

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # Videos
    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("duration", sa.Float(), nullable=False),
        sa.Column("fps", sa.Float(), nullable=False),
        sa.Column("is_saved", sa.Boolean(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_path"),
    )
    op.create_index(op.f("ix_videos_id"), "videos", ["id"], unique=False)
    op.create_index(op.f("ix_videos_user_id"), "videos", ["user_id"], unique=False)

    # Analyses
    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "PROCESSING", "COMPLETED", "FAILED", name="analysisstatus", native_enum=False), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("music_score", sa.Float(), nullable=True),
        sa.Column("rhythm_score", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analyses_id"), "analyses", ["id"], unique=False)
    op.create_index(op.f("ix_analyses_video_id"), "analyses", ["video_id"], unique=False)
    op.create_index(op.f("ix_analyses_status"), "analyses", ["status"], unique=False)

    # Errors
    op.create_table(
        "errors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("analysis_id", sa.Integer(), nullable=False),
        sa.Column("element_name", sa.String(length=255), nullable=False),
        sa.Column("timestamp", sa.Float(), nullable=False),
        sa.Column("error_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="errorseverity", native_enum=False), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("screenshot_path", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_errors_id"), "errors", ["id"], unique=False)
    op.create_index(op.f("ix_errors_analysis_id"), "errors", ["analysis_id"], unique=False)
    op.create_index(op.f("ix_errors_element_name"), "errors", ["element_name"], unique=False)

    # TempUploads
    op.create_table(
        "temp_uploads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("analysis_id", sa.Integer(), nullable=True),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id"),
    )
    op.create_index(op.f("ix_temp_uploads_id"), "temp_uploads", ["id"], unique=False)
    op.create_index(op.f("ix_temp_uploads_user_id"), "temp_uploads", ["user_id"], unique=False)
    op.create_index(op.f("ix_temp_uploads_video_id"), "temp_uploads", ["video_id"], unique=False)
    op.create_index(op.f("ix_temp_uploads_analysis_id"), "temp_uploads", ["analysis_id"], unique=False)
    op.create_index(op.f("ix_temp_uploads_expires_at"), "temp_uploads", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_table("temp_uploads")
    op.drop_table("errors")
    op.drop_table("analyses")
    op.drop_table("videos")
    op.drop_table("users")
