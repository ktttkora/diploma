"""
Cleanup Celery tasks.

Periodic maintenance: removing expired temporary uploads and orphaned files.
"""

from typing import Dict, Any
from datetime import datetime
from pathlib import Path

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.temp_upload import TempUpload
from app.models.video import Video
from app.models.analysis import Analysis
from app.models.error import Error
from app.services.storage_service import storage_service
from app.config import settings


@celery_app.task(name="app.tasks.cleanup_tasks.cleanup_expired_uploads")
def cleanup_expired_uploads() -> Dict[str, Any]:
    """
    Delete temporary uploads whose expiry has passed.

    Saved videos are left alone: their expiry record is removed when the
    user saves the analysis, and this task skips saved videos regardless.

    Returns:
        Dict with cleanup statistics
    """
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        expired = db.query(TempUpload).filter(TempUpload.expires_at < now).all()

        deleted_files = 0
        deleted_videos = 0
        skipped_saved = 0

        for upload in expired:
            video = db.query(Video).filter(Video.id == upload.video_id).first()

            if video and video.is_saved:
                # Safety net: a saved video must never expire
                db.delete(upload)
                skipped_saved += 1
                continue

            if video:
                # Remove screenshots belonging to this video's analyses
                errors = (
                    db.query(Error)
                    .join(Analysis, Error.analysis_id == Analysis.id)
                    .filter(Analysis.video_id == video.id)
                    .all()
                )
                for error in errors:
                    if error.screenshot_path:
                        storage_service.delete_file(error.screenshot_path)

                if storage_service.delete_file(video.file_path):
                    deleted_files += 1

                db.delete(video)
                deleted_videos += 1
            else:
                if storage_service.delete_file(upload.file_path):
                    deleted_files += 1

            db.delete(upload)

        db.commit()

        return {
            "status": "completed",
            "deleted_files": deleted_files,
            "deleted_videos": deleted_videos,
            "skipped_saved": skipped_saved,
            "checked_at": now.isoformat()
        }

    except Exception as exc:
        db.rollback()
        return {"status": "failed", "error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.cleanup_tasks.cleanup_orphaned_files")
def cleanup_orphaned_files() -> Dict[str, Any]:
    """
    Delete files on disk that no database row references.

    Scans the upload and temp directories. Files newer than one hour are
    kept, so an upload still being written is never deleted.

    Returns:
        Dict with cleanup statistics
    """
    db = SessionLocal()
    try:
        known_paths = {video.file_path for video in db.query(Video).all()}
        known_paths |= {upload.file_path for upload in db.query(TempUpload).all()}

        # Normalise for comparison: DB rows may use either separator
        known_normalised = {str(Path(p)) for p in known_paths}

        deleted = 0
        cutoff = datetime.utcnow().timestamp() - 3600

        for directory in (settings.UPLOAD_FOLDER, settings.TEMP_FOLDER):
            path = Path(directory)
            if not path.exists():
                continue

            for file_path in path.iterdir():
                if not file_path.is_file():
                    continue

                if str(file_path) in known_normalised:
                    continue

                # Leave recently created files alone
                if file_path.stat().st_mtime > cutoff:
                    continue

                file_path.unlink()
                deleted += 1

        return {"status": "completed", "deleted": deleted}

    except Exception as exc:
        return {"status": "failed", "error": str(exc)}
    finally:
        db.close()
