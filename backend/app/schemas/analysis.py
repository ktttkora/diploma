"""
Analysis Pydantic schemas.

Defines request/response models for analysis-related API endpoints.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from app.models.analysis import AnalysisStatus


class AnalysisCreate(BaseModel):
    """Schema for creating a new analysis."""
    video_id: int = Field(..., description="Video ID to analyze")


class AnalysisResponse(BaseModel):
    """Schema for analysis data in API responses."""
    id: int
    video_id: int
    status: AnalysisStatus
    overall_score: Optional[float]
    music_score: Optional[float]
    rhythm_score: Optional[float]
    started_at: datetime
    completed_at: Optional[datetime]

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
    overall_score: Optional[float]
    music_score: Optional[float]
    rhythm_score: Optional[float]
    started_at: datetime
    completed_at: Optional[datetime]
    errors: List["ErrorResponse"]

    class Config:
        from_attributes = True


# Forward reference for ErrorResponse
from app.schemas.error import ErrorResponse
AnalysisDetailResponse.model_rebuild()
