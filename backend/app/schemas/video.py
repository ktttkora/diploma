"""
Video Pydantic schemas.

Defines request/response models for video-related API endpoints.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class VideoUpload(BaseModel):
    """Schema for video upload metadata."""
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type (video/mp4, video/avi, etc.)")


class VideoResponse(BaseModel):
    """Schema for video data in API responses."""
    id: int
    user_id: int
    filename: str
    file_path: str
    file_size: int
    duration: Optional[float]
    uploaded_at: datetime

    class Config:
        from_attributes = True


class VideoListResponse(BaseModel):
    """Schema for paginated video list."""
    videos: list[VideoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class VideoDeleteResponse(BaseModel):
    """Schema for video deletion confirmation."""
    message: str
    video_id: int
