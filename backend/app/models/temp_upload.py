"""
TempUpload database model.

Tracks temporary uploads before user saves or discards them.
"""

from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from typing import Optional

from app.db.session import Base


class TempUpload(Base):
    """
    TempUpload model for tracking temporary file uploads.

    Used to track uploads before user decides to save or discard.
    Expired uploads (>24h) are cleaned up by Celery Beat task.

    Attributes:
        id: Primary key
        user_id: Uploader user ID (foreign key)
        video_id: Associated video ID (foreign key)
        analysis_id: Associated analysis ID (foreign key, optional)
        file_path: Path to temporary file
        uploaded_at: Upload timestamp
        expires_at: Expiration timestamp (24h after upload)
        owner: Related User
        video: Related Video
        analysis: Related Analysis (if processing started)
    """

    __tablename__ = "temp_uploads"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    analysis_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    file_path: Mapped[str] = mapped_column(String(512), nullable=False)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True  # For efficient cleanup queries
    )

    # Relationships
    owner: Mapped["User"] = relationship("User")
    video: Mapped["Video"] = relationship("Video")
    analysis: Mapped[Optional["Analysis"]] = relationship("Analysis")

    def __repr__(self) -> str:
        return f"<TempUpload(id={self.id}, video_id={self.video_id}, expires_at={self.expires_at})>"

    @classmethod
    def create_with_expiry(cls, user_id: int, video_id: int, file_path: str, hours: int = 24):
        """
        Create a new temp upload with automatic expiry calculation.

        Args:
            user_id: Owner user ID
            video_id: Associated video ID
            file_path: Path to temporary file
            hours: Hours until expiration (default 24)

        Returns:
            TempUpload instance (not committed to DB yet)
        """
        now = datetime.utcnow()
        expires = now + timedelta(hours=hours)

        return cls(
            user_id=user_id,
            video_id=video_id,
            file_path=file_path,
            uploaded_at=now,
            expires_at=expires
        )
