"""
Error Pydantic schemas.

Defines request/response models for error-related API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional
from app.models.error import ErrorSeverity


class ErrorResponse(BaseModel):
    """Schema for error data in API responses."""
    id: int
    analysis_id: int
    element_name: str
    timestamp: float
    error_type: str
    severity: ErrorSeverity
    description: str
    screenshot_path: Optional[str]

    class Config:
        from_attributes = True


class ErrorListResponse(BaseModel):
    """Schema for paginated error list."""
    errors: list[ErrorResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorFilterParams(BaseModel):
    """Schema for error filtering parameters."""
    element_name: Optional[str] = Field(None, description="Filter by dance element")
    severity: Optional[ErrorSeverity] = Field(None, description="Filter by severity level")
    min_timestamp: Optional[float] = Field(None, description="Minimum timestamp (seconds)")
    max_timestamp: Optional[float] = Field(None, description="Maximum timestamp (seconds)")
