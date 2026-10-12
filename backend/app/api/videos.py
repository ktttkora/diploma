"""
Video API endpoints.

Provides video upload, retrieval, and deletion functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import subprocess

from app.db.session import get_db
from app.models.user import User
from app.models.video import Video
from app.schemas.video import VideoResponse, VideoListResponse, VideoDeleteResponse
from app.api.deps import get_current_user
from app.services.storage_service import storage_service
from app.config import settings


router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.post("/", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
def upload_video(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a new video.

    Args:
        file: Video file (multipart/form-data)
        current_user: Authenticated user
        db: Database session

    Returns:
        Created video object

    Raises:
        HTTPException 400: If file type is not supported
        HTTPException 413: If file is too large
    """
    # Validate content type
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a video"
        )

    # Check file size (read first to get size)
    contents = file.file.read()
    file_size = len(contents)

    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large (max {settings.MAX_UPLOAD_SIZE} bytes)"
        )

    # Save file
    from io import BytesIO
    file_obj = BytesIO(contents)
    file_path, file_size = storage_service.save_uploaded_video(
        file_obj,
        current_user.id,
        file.filename or "video.mp4"
    )

    # Get video duration and FPS using ffprobe
    duration = 0.0
    fps = 30.0
    try:
        # Get duration
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            duration = float(result.stdout.strip())

        # Get FPS
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=r_frame_rate",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            fps_str = result.stdout.strip()
            if "/" in fps_str:
                num, den = fps_str.split("/")
                fps = float(num) / float(den)
    except Exception:
        pass  # Use defaults

    # Create video record
    new_video = Video(
        user_id=current_user.id,
        filename=file.filename or "video.mp4",
        file_path=file_path,
        file_size=file_size,
        duration=duration,
        fps=fps
    )

    db.add(new_video)
    db.commit()
    db.refresh(new_video)

    return new_video


@router.get("/", response_model=VideoListResponse)
def list_videos(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of user's videos.

    Args:
        page: Page number (1-indexed)
        page_size: Items per page (max 100)
        current_user: Authenticated user
        db: Database session

    Returns:
        Paginated list of videos
    """
    # Get total count
    total = db.query(func.count(Video.id)).filter(Video.user_id == current_user.id).scalar()

    # Get paginated videos
    offset = (page - 1) * page_size
    videos = db.query(Video)\
        .filter(Video.user_id == current_user.id)\
        .order_by(Video.uploaded_at.desc())\
        .offset(offset)\
        .limit(page_size)\
        .all()

    total_pages = (total + page_size - 1) // page_size

    return VideoListResponse(
        videos=videos,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a single video by ID.

    Args:
        video_id: Video ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Video object

    Raises:
        HTTPException 404: If video not found or not owned by user
    """
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id
    ).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    return video


@router.delete("/{video_id}", response_model=VideoDeleteResponse)
def delete_video(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a video and its file.

    Also deletes related analyses and errors (CASCADE).

    Args:
        video_id: Video ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Deletion confirmation

    Raises:
        HTTPException 404: If video not found or not owned by user
    """
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id
    ).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Delete file from storage
    storage_service.delete_file(video.file_path)

    # Delete database record (CASCADE will delete analyses and errors)
    db.delete(video)
    db.commit()

    return VideoDeleteResponse(
        message="Video deleted successfully",
        video_id=video_id
    )
