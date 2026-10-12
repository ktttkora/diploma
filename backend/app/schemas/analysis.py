"""
Analysis Pydantic schemas.

Defines request/response models for analysis-related API endpoints.
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from app.models.analysis import AnalysisStatus


class AnalysisResponse(BaseModel):
    """Schema for analysis data in API responses."""
    id: int
    video_id: int
    status: AnalysisStatus
    overall_score: Optional[float] = None
    rhythm_score: Optional[float] = None
    posture_score: Optional[float] = None
    technique_score: Optional[float] = None
    music_score: Optional[float] = None
    total_errors: int = 0
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AnalysisStatusResponse(BaseModel):
    """Schema for polling analysis progress."""
    id: int
    status: AnalysisStatus
    total_errors: int = 0
    overall_score: Optional[float] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class AnalysisListResponse(BaseModel):
    """Schema for paginated analysis list."""
    analyses: List[AnalysisResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AnalysisDetailResponse(BaseModel):
    """Schema for detailed analysis with errors."""
    id: int
    video_id: int
    status: AnalysisStatus
    overall_score: Optional[float] = None
    rhythm_score: Optional[float] = None
    posture_score: Optional[float] = None
    technique_score: Optional[float] = None
    music_score: Optional[float] = None
    total_errors: int = 0
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    errors: List["ErrorResponse"] = []

    class Config:
        from_attributes = True


class SaveAnalysisResponse(BaseModel):
    """Schema for save/discard confirmation."""
    message: str
    analysis_id: int
    video_id: int
    is_saved: bool


# Resolve the forward reference to ErrorResponse
from app.schemas.error import ErrorResponse  # noqa: E402

AnalysisDetailResponse.model_rebuild()
