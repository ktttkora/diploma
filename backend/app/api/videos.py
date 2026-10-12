"""
Video API endpoints.

Handles upload (which queues an analysis), listing, retrieval, and deletion.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from pathlib import Path

from app.db.session import get_db
from app.models.user import User
from app.models.video import Video
from app.models.analysis import Analysis, AnalysisStatus
from app.models.temp_upload import TempUpload
from app.schemas.video import (
    VideoResponse,
    VideoListResponse,
    VideoDeleteResponse,
    VideoUploadResponse,
)
from app.api.deps import get_current_user, get_current_user_media
from app.services.storage_service import storage_service
from app.utils.video_utils import get_video_info
from app.config import settings


router = APIRouter(prefix="/api/videos", tags=["videos"])

ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


def _validate_upload(file: UploadFile) -> None:
    """
    Validate an uploaded file's type and extension.

    Args:
        file: Uploaded file

    Raises:
        HTTPException 400: If the file is not a supported video
    """
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a video"
        )

    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )


def _read_probe_metadata(file_path: str) -> tuple[float, float]:
    """
    Read duration and FPS with ffprobe.

    Args:
        file_path: Path to the video file

    Returns:
        Tuple of (duration_seconds, fps). Falls back to (0.0, 30.0) on failure.
    """
    duration = 0.0
    fps = 30.0

    try:
        info = get_video_info(file_path)
        duration = float(info.get("duration", 0.0))
        fps = float(info.get("fps", 30.0))
    except Exception:
        pass  # Keep defaults; duration is validated by the caller

    return duration, fps


@router.post("/", response_model=VideoUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_video(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a video and queue its analysis.

    The file is stored in temporary storage and an analysis job is queued.
    The user decides later whether to save the result permanently.

    Args:
        file: Video file (multipart/form-data)
        current_user: Authenticated user
        db: Database session

    Returns:
        Video and analysis IDs with the initial analysis status

    Raises:
        HTTPException 400: If the file type or duration is unsupported
        HTTPException 413: If the file is too large
    """
    _validate_upload(file)

    contents = file.file.read()
    file_size = len(contents)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty"
        )

    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large (max {settings.MAX_UPLOAD_SIZE} bytes)"
        )

    # Store in temporary storage until the user saves the result
    from io import BytesIO
    temp_id = f"{current_user.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
    file_path, file_size = storage_service.save_temp_video(BytesIO(contents), temp_id)

    duration, fps = _read_probe_metadata(file_path)

    if duration > settings.MAX_VIDEO_DURATION:
        storage_service.delete_file(file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Video too long ({duration:.0f}s). "
                f"Maximum is {settings.MAX_VIDEO_DURATION}s"
            )
        )

    video = Video(
        user_id=current_user.id,
        filename=file.filename or "video.mp4",
        file_path=file_path,
        file_size=file_size,
        duration=duration,
        fps=fps,
        is_saved=False
    )
    db.add(video)
    db.flush()

    analysis = Analysis(
        video_id=video.id,
        status=AnalysisStatus.PENDING
    )
    db.add(analysis)
    db.flush()

    # Temporary uploads expire unless the user saves them
    temp_upload = TempUpload.create_with_expiry(
        user_id=current_user.id,
        video_id=video.id,
        file_path=file_path,
        hours=settings.TEMP_UPLOAD_TTL_HOURS
    )
    temp_upload.analysis_id = analysis.id
    db.add(temp_upload)

    db.commit()
    db.refresh(video)
    db.refresh(analysis)

    # Queue processing. A broker outage must not lose the upload, so the
    # failure is recorded on the analysis instead of raising.
    try:
        from app.tasks.video_tasks import process_video_task
        process_video_task.delay(video.id, analysis.id)
    except Exception as exc:
        analysis.status = AnalysisStatus.FAILED
        analysis.error_message = f"Could not queue processing: {exc}"
        db.commit()

    return VideoUploadResponse(
        video=VideoResponse.model_validate(video),
        analysis_id=analysis.id,
        status=analysis.status
    )


@router.get("/", response_model=VideoListResponse)
def list_videos(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    saved_only: bool = Query(False, description="Return only saved videos"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a paginated list of the current user's videos.

    Args:
        page: Page number (1-indexed)
        page_size: Items per page (max 100)
        saved_only: If true, only videos the user saved
        current_user: Authenticated user
        db: Database session

    Returns:
        Paginated list of videos
    """
    base_query = db.query(Video).filter(Video.user_id == current_user.id)
    count_query = db.query(func.count(Video.id)).filter(Video.user_id == current_user.id)

    if saved_only:
        base_query = base_query.filter(Video.is_saved.is_(True))
        count_query = count_query.filter(Video.is_saved.is_(True))

    total = count_query.scalar() or 0

    offset = (page - 1) * page_size
    videos = (
        base_query
        .order_by(Video.uploaded_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    total_pages = (total + page_size - 1) // page_size

    return VideoListResponse(
        videos=videos,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/history", response_model=VideoListResponse)
def get_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the user's saved videos (their analysis history).

    Args:
        page: Page number (1-indexed)
        page_size: Items per page (max 100)
        current_user: Authenticated user
        db: Database session

    Returns:
        Paginated list of saved videos
    """
    return list_videos(
        page=page,
        page_size=page_size,
        saved_only=True,
        current_user=current_user,
        db=db
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
        HTTPException 404: If the video does not exist or belongs to another user
    """
    video = (
        db.query(Video)
        .filter(Video.id == video_id, Video.user_id == current_user.id)
        .first()
    )

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    return video


@router.get("/{video_id}/stream")
def stream_video(
    video_id: int,
    current_user: User = Depends(get_current_user_media),
    db: Session = Depends(get_db)
):
    """
    Stream a video file for playback in the results page.

    Videos live outside the web root, so they are served through this
    authenticated endpoint. Accepts the token as a query parameter because
    a <video> element cannot send an Authorization header.

    Args:
        video_id: Video ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Video file

    Raises:
        HTTPException 404: If the video or its file is missing
    """
    video = (
        db.query(Video)
        .filter(Video.id == video_id, Video.user_id == current_user.id)
        .first()
    )

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    path = Path(video.file_path)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video file is missing"
        )

    return FileResponse(str(path), media_type="video/mp4", filename=video.filename)


@router.delete("/{video_id}", response_model=VideoDeleteResponse)
def delete_video(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a video, its file, and all related analyses and errors.

    Args:
        video_id: Video ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Deletion confirmation

    Raises:
        HTTPException 404: If the video does not exist or belongs to another user
    """
    video = (
        db.query(Video)
        .filter(Video.id == video_id, Video.user_id == current_user.id)
        .first()
    )

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Remove screenshots belonging to this video's analyses
    from app.models.error import Error
    errors = (
        db.query(Error)
        .join(Analysis, Error.analysis_id == Analysis.id)
        .filter(Analysis.video_id == video_id)
        .all()
    )
    for error in errors:
        if error.screenshot_path:
            storage_service.delete_file(error.screenshot_path)

    storage_service.delete_file(video.file_path)

    # Cascades to analyses, errors, and the temp-upload marker
    db.delete(video)
    db.commit()

    return VideoDeleteResponse(
        message="Video deleted successfully",
        video_id=video_id
    )
