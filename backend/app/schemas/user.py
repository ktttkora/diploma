"""
User Pydantic schemas.

Defines request/response models for user-related API endpoints.
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import List, Optional


class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=100, description="User password (min 8 characters)")


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserUpdate(BaseModel):
    """Schema for user profile update."""
    email: Optional[EmailStr] = Field(None, description="New email address")
    password: Optional[str] = Field(None, min_length=8, max_length=100, description="New password")
    display_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Name shown in the profile. Empty string clears it."
    )


class UserResponse(BaseModel):
    """Schema for user data in API responses."""
    id: int
    email: str
    display_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Allows creation from ORM models


class ScoreAverages(BaseModel):
    """Mean scores across saved analyses. Missing categories stay null."""
    overall: Optional[float] = None
    rhythm: Optional[float] = None
    posture: Optional[float] = None
    technique: Optional[float] = None
    music: Optional[float] = None


class FrequentError(BaseModel):
    """How often one error type appears in saved analyses."""
    error_type: str
    count: int


class ProgressPoint(BaseModel):
    """One saved analysis on the progress timeline."""
    analysis_id: int
    completed_at: Optional[datetime] = None
    overall_score: Optional[float] = None
    rhythm_score: Optional[float] = None
    posture_score: Optional[float] = None
    technique_score: Optional[float] = None
    music_score: Optional[float] = None


class UserStatsResponse(BaseModel):
    """Progress statistics for the profile page."""
    saved_analyses: int
    average_scores: ScoreAverages
    top_errors: List[FrequentError]
    progress: List[ProgressPoint]


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for decoded token data."""
    email: Optional[str] = None
