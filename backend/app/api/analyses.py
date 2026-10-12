"""
Analysis API endpoints.

Provides analysis retrieval and management functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.db.session import get_db
from app.models.user import User
from app.models.video import Video
from app.models.analysis import Analysis
from app.models.error import Error
from app.schemas.analysis import AnalysisResponse, AnalysisListResponse, AnalysisDetailResponse
from app.schemas.error import ErrorResponse, ErrorListResponse
from app.api.deps import get_current_user


router = APIRouter(prefix="/api/analyses", tags=["analyses"])


@router.get("/", response_model=AnalysisListResponse)
def list_analyses(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of user's analyses.

    Args:
        page: Page number (1-indexed)
        page_size: Items per page (max 100)
        current_user: Authenticated user
        db: Database session

    Returns:
        Paginated list of analyses
    """
    # Get total count (user's analyses through videos)
    total = db.query(func.count(Analysis.id))\
        .join(Video, Analysis.video_id == Video.id)\
        .filter(Video.user_id == current_user.id)\
        .scalar()

    # Get paginated analyses
    offset = (page - 1) * page_size
    analyses = db.query(Analysis)\
        .join(Video, Analysis.video_id == Video.id)\
        .filter(Video.user_id == current_user.id)\
        .order_by(Analysis.started_at.desc())\
        .offset(offset)\
        .limit(page_size)\
        .all()

    total_pages = (total + page_size - 1) // page_size

    return AnalysisListResponse(
        analyses=analyses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{analysis_id}", response_model=AnalysisDetailResponse)
def get_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a single analysis with errors by ID.

    Args:
        analysis_id: Analysis ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Analysis with errors

    Raises:
        HTTPException 404: If analysis not found or not owned by user
    """
    analysis = db.query(Analysis)\
        .join(Video, Analysis.video_id == Video.id)\
        .filter(Analysis.id == analysis_id, Video.user_id == current_user.id)\
        .first()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )

    # Get errors
    errors = db.query(Error)\
        .filter(Error.analysis_id == analysis_id)\
        .order_by(Error.timestamp)\
        .all()

    return AnalysisDetailResponse(
        id=analysis.id,
        video_id=analysis.video_id,
        status=analysis.status,
        overall_score=analysis.overall_score,
        music_score=analysis.music_score,
        rhythm_score=analysis.rhythm_score,
        started_at=analysis.started_at,
        completed_at=analysis.completed_at,
        errors=errors
    )


@router.get("/{analysis_id}/errors", response_model=ErrorListResponse)
def list_analysis_errors(
    analysis_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of errors for an analysis.

    Args:
        analysis_id: Analysis ID
        page: Page number (1-indexed)
        page_size: Items per page (max 100)
        current_user: Authenticated user
        db: Database session

    Returns:
        Paginated list of errors

    Raises:
        HTTPException 404: If analysis not found or not owned by user
    """
    # Verify analysis belongs to user
    analysis = db.query(Analysis)\
        .join(Video, Analysis.video_id == Video.id)\
        .filter(Analysis.id == analysis_id, Video.user_id == current_user.id)\
        .first()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )

    # Get total count
    total = db.query(func.count(Error.id))\
        .filter(Error.analysis_id == analysis_id)\
        .scalar()

    # Get paginated errors
    offset = (page - 1) * page_size
    errors = db.query(Error)\
        .filter(Error.analysis_id == analysis_id)\
        .order_by(Error.timestamp)\
        .offset(offset)\
        .limit(page_size)\
        .all()

    total_pages = (total + page_size - 1) // page_size

    return ErrorListResponse(
        errors=errors,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an analysis and its errors.

    Args:
        analysis_id: Analysis ID
        current_user: Authenticated user
        db: Database session

    Returns:
        No content (204)

    Raises:
        HTTPException 404: If analysis not found or not owned by user
    """
    analysis = db.query(Analysis)\
        .join(Video, Analysis.video_id == Video.id)\
        .filter(Analysis.id == analysis_id, Video.user_id == current_user.id)\
        .first()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )

    # Delete screenshots
    errors = db.query(Error).filter(Error.analysis_id == analysis_id).all()

    from app.services.storage_service import storage_service
    for error in errors:
        if error.screenshot_path:
            storage_service.delete_file(error.screenshot_path)

    # Delete analysis (CASCADE will delete errors)
    db.delete(analysis)
    db.commit()

    return None
