"""
Video database model.

Represents user-uploaded dance videos.
"""

from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List

from app.db.session import Base


class Video(Base):
    """
    Video model for user uploads.

    Attributes:
        id: Primary key
        user_id: Owner user ID (foreign key)
        filename: Original filename
        file_path: Path to video file on disk
        file_size: File size in bytes
        duration: Video duration in seconds
        fps: Frames per second
        is_saved: Whether user saved this video (vs temp upload)
        uploaded_at: Upload timestamp
        saved_at: When user clicked "save" (null if not saved yet)
        owner: Related User
        analyses: Related Analysis results
    """

    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    fps: Mapped[float] = mapped_column(Float, nullable=False)

    is_saved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    saved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="videos")
    analyses: Mapped[List["Analysis"]] = relationship(
        "Analysis",
        back_populates="video",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Video(id={self.id}, filename={self.filename}, is_saved={self.is_saved})>"
