"""
Analysis API endpoints.

Provides analysis retrieval, polling, save/discard, and screenshot serving.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from pathlib import Path
from typing import List

from app.db.session import get_db
from app.models.user import User
from app.models.video import Video
from app.models.analysis import Analysis, AnalysisStatus
from app.models.error import Error
from app.models.temp_upload import TempUpload
from app.schemas.analysis import (
    AnalysisResponse,
    AnalysisStatusResponse,
    AnalysisListResponse,
    AnalysisDetailResponse,
    SaveAnalysisResponse,
)
from app.schemas.error import ErrorListResponse
from app.api.deps import get_current_user, get_current_user_media
from app.services.storage_service import storage_service


router = APIRouter(prefix="/api/analyses", tags=["analyses"])


def _get_owned_analysis(analysis_id: int, user_id: int, db: Session) -> Analysis:
    """
    Load an analysis that belongs to the given user.

    Args:
        analysis_id: Analysis ID
        user_id: Owner user ID
        db: Database session

    Returns:
        Analysis instance

    Raises:
        HTTPException 404: If the analysis does not exist or belongs to another user
    """
    analysis = (
        db.query(Analysis)
        .join(Video, Analysis.video_id == Video.id)
        .filter(Analysis.id == analysis_id, Video.user_id == user_id)
        .first()
    )

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )

    return analysis


@router.get("/", response_model=AnalysisListResponse)
def list_analyses(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    saved_only: bool = Query(False, description="Return only saved analyses"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of the current user's analyses.

    Args:
        page: Page number (1-indexed)
        page_size: Items per page (max 100)
        saved_only: If true, only analyses whose video was saved
        current_user: Authenticated user
        db: Database session

    Returns:
        Paginated list of analyses
    """
    base_query = (
        db.query(Analysis)
        .join(Video, Analysis.video_id == Video.id)
        .filter(Video.user_id == current_user.id)
    )
    count_query = (
        db.query(func.count(Analysis.id))
        .join(Video, Analysis.video_id == Video.id)
        .filter(Video.user_id == current_user.id)
    )

    if saved_only:
        base_query = base_query.filter(Video.is_saved.is_(True))
        count_query = count_query.filter(Video.is_saved.is_(True))

    total = count_query.scalar() or 0

    offset = (page - 1) * page_size
    analyses = (
        base_query
        .order_by(Analysis.started_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

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
    Get a single analysis with its errors.

    Args:
        analysis_id: Analysis ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Analysis with errors
    """
    analysis = _get_owned_analysis(analysis_id, current_user.id, db)

    errors = (
        db.query(Error)
        .filter(Error.analysis_id == analysis_id)
        .order_by(Error.timestamp)
        .all()
    )

    return AnalysisDetailResponse(
        id=analysis.id,
        video_id=analysis.video_id,
        status=analysis.status,
        overall_score=analysis.overall_score,
        rhythm_score=analysis.rhythm_score,
        posture_score=analysis.posture_score,
        technique_score=analysis.technique_score,
        music_score=analysis.music_score,
        total_errors=analysis.total_errors,
        processing_time=analysis.processing_time,
        error_message=analysis.error_message,
        started_at=analysis.started_at,
        completed_at=analysis.completed_at,
        errors=errors
    )


@router.get("/{analysis_id}/status", response_model=AnalysisStatusResponse)
def get_analysis_status(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get lightweight analysis status for polling.

    Args:
        analysis_id: Analysis ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Status, error count, score, and failure message
    """
    analysis = _get_owned_analysis(analysis_id, current_user.id, db)

    return AnalysisStatusResponse(
        id=analysis.id,
        status=analysis.status,
        total_errors=analysis.total_errors,
        overall_score=analysis.overall_score,
        error_message=analysis.error_message
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
    """
    _get_owned_analysis(analysis_id, current_user.id, db)

    total = (
        db.query(func.count(Error.id))
        .filter(Error.analysis_id == analysis_id)
        .scalar() or 0
    )

    offset = (page - 1) * page_size
    errors = (
        db.query(Error)
        .filter(Error.analysis_id == analysis_id)
        .order_by(Error.timestamp)
        .offset(offset)
        .limit(page_size)
        .all()
    )

    total_pages = (total + page_size - 1) // page_size

    return ErrorListResponse(
        errors=errors,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{analysis_id}/errors/{error_id}/screenshot")
def get_error_screenshot(
    analysis_id: int,
    error_id: int,
    current_user: User = Depends(get_current_user_media),
    db: Session = Depends(get_db)
):
    """
    Serve the composite screenshot for an error.

    Screenshots are stored outside the web root, so they are streamed
    through this authenticated endpoint. Accepts the token as a query
    parameter because an <img> element cannot send an Authorization header.

    Args:
        analysis_id: Analysis ID
        error_id: Error ID
        current_user: Authenticated user
        db: Database session

    Returns:
        JPEG image

    Raises:
        HTTPException 404: If the error or its screenshot does not exist
    """
    _get_owned_analysis(analysis_id, current_user.id, db)

    error = (
        db.query(Error)
        .filter(Error.id == error_id, Error.analysis_id == analysis_id)
        .first()
    )

    if not error or not error.screenshot_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot not found"
        )

    path = Path(error.screenshot_path)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot file is missing"
        )

    return FileResponse(str(path), media_type="image/jpeg")


@router.post("/{analysis_id}/save", response_model=SaveAnalysisResponse)
def save_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Save an analysis permanently.

    Moves the video out of temporary storage, marks it saved, and clears the
    expiry record so the cleanup task leaves it alone.

    Args:
        analysis_id: Analysis ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Confirmation with the new saved state

    Raises:
        HTTPException 404: If the analysis does not exist
        HTTPException 409: If the analysis has not finished processing
    """
    analysis = _get_owned_analysis(analysis_id, current_user.id, db)

    if analysis.status not in (AnalysisStatus.COMPLETED, AnalysisStatus.FAILED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis is still processing"
        )

    video = db.query(Video).filter(Video.id == analysis.video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Move the file from temp storage into permanent uploads
    if not video.is_saved:
        current_path = Path(video.file_path)
        temp_root = Path(storage_service.temp_dir)

        if current_path.exists() and temp_root in current_path.parents:
            new_path = storage_service.move_temp_to_uploads(
                video.file_path,
                current_user.id,
                video.filename
            )
            video.file_path = new_path

        video.is_saved = True
        video.saved_at = datetime.utcnow()

    # Saved videos no longer expire
    temp_upload = (
        db.query(TempUpload)
        .filter(TempUpload.video_id == video.id)
        .first()
    )
    if temp_upload:
        db.delete(temp_upload)

    db.commit()
    db.refresh(video)

    return SaveAnalysisResponse(
        message="Analysis saved",
        analysis_id=analysis_id,
        video_id=video.id,
        is_saved=video.is_saved
    )


@router.delete("/{analysis_id}", response_model=SaveAnalysisResponse)
def discard_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Discard an analysis: delete the video file and all related records.

    Removes the source video, every error screenshot, and the rows for the
    analysis, its errors, and the temporary-upload marker.

    Args:
        analysis_id: Analysis ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Confirmation of the deletion

    Raises:
        HTTPException 404: If the analysis does not exist
    """
    analysis = _get_owned_analysis(analysis_id, current_user.id, db)

    video = db.query(Video).filter(Video.id == analysis.video_id).first()

    # Delete error screenshots first, then the video file itself
    errors = db.query(Error).filter(Error.analysis_id == analysis_id).all()
    for error in errors:
        if error.screenshot_path:
            storage_service.delete_file(error.screenshot_path)

    video_id = analysis.video_id

    if video:
        storage_service.delete_file(video.file_path)

        # Deleting the video cascades to its analyses, errors, and temp record
        db.delete(video)
    else:
        db.delete(analysis)

    db.commit()

    return SaveAnalysisResponse(
        message="Analysis discarded",
        analysis_id=analysis_id,
        video_id=video_id,
        is_saved=False
    )
