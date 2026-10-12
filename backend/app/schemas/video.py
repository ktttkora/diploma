"""
Video Pydantic schemas.

Defines request/response models for video-related API endpoints.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from app.models.analysis import AnalysisStatus


class VideoResponse(BaseModel):
    """Schema for video data in API responses."""
    id: int
    user_id: int
    filename: str
    file_size: int
    duration: float
    fps: float
    is_saved: bool
    uploaded_at: datetime
    saved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VideoUploadResponse(BaseModel):
    """Schema returned after a successful upload."""
    video: VideoResponse
    analysis_id: int
    status: AnalysisStatus


class VideoListResponse(BaseModel):
    """Schema for paginated video list."""
    videos: List[VideoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class VideoDeleteResponse(BaseModel):
    """Schema for video deletion confirmation."""
    message: str
    video_id: int
