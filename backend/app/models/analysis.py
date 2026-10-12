"""
Analysis database model.

Represents analysis results for uploaded videos.
"""

from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List
import enum

from app.db.session import Base


class AnalysisStatus(str, enum.Enum):
    """Analysis processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Analysis(Base):
    """
    Analysis model for video processing results.

    Attributes:
        id: Primary key
        video_id: Analyzed video ID (foreign key)
        status: Processing status
        overall_score: Combined score (0-100)
        rhythm_score: Rhythm matching score (0-100)
        posture_score: Posture score from AI analysis (0-100)
        technique_score: Technique score from AI analysis (0-100)
        music_score: Musicality score (0-100)
        total_errors: Number of errors found
        processing_time: Seconds spent processing
        ai_response: Raw AI response (JSON string) for debugging
        error_message: Failure reason when status is FAILED
        started_at: When analysis started
        completed_at: When analysis finished (null if not completed)
        video: Related Video
        errors: Related detected errors
    """

    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    status: Mapped[AnalysisStatus] = mapped_column(
        SQLEnum(AnalysisStatus, native_enum=False),
        default=AnalysisStatus.PENDING,
        nullable=False,
        index=True
    )

    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rhythm_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    posture_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    technique_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    music_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    total_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processing_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    video: Mapped["Video"] = relationship("Video", back_populates="analyses")
    errors: Mapped[List["Error"]] = relationship(
        "Error",
        back_populates="analysis",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Analysis(id={self.id}, video_id={self.video_id}, status={self.status})>"
