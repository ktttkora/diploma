"""
Error database model.

Represents detected technique errors in analyzed videos.
"""

from sqlalchemy import String, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
import enum

from app.db.session import Base


class ErrorSeverity(str, enum.Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Error(Base):
    """
    Error model for detected technique mistakes.

    Attributes:
        id: Primary key
        analysis_id: Parent analysis ID (foreign key)
        element_name: Name of dance element being performed
        timestamp: When error occurred in video (seconds)
        error_type: Type of error (e.g., "arm_position", "footwork")
        severity: Error severity level
        description: Human-readable error description
        screenshot_path: Path to composite screenshot (user + reference side-by-side)
        analysis: Related Analysis
    """

    __tablename__ = "errors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    analysis_id: Mapped[int] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    element_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    error_type: Mapped[str] = mapped_column(String(100), nullable=False)

    severity: Mapped[ErrorSeverity] = mapped_column(
        SQLEnum(ErrorSeverity, native_enum=False),
        default=ErrorSeverity.MEDIUM,
        nullable=False
    )

    description: Mapped[str] = mapped_column(String(1000), nullable=False)

    # CRITICAL: Only ONE screenshot_path (composite: user + reference side-by-side)
    screenshot_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Relationships
    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="errors")

    def __repr__(self) -> str:
        return f"<Error(id={self.id}, element={self.element_name}, severity={self.severity})>"
