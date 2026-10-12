"""
Cleanup Celery tasks.

Periodic tasks for maintenance: removing expired temp uploads,
orphaned files, and old analyses.
"""

from celery import shared_task
from typing import Dict, Any
from datetime import datetime

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.temp_upload import TempUpload
from app.models.video import Video
from app.services.storage_service import storage_service


@celery_app.task(name="app.tasks.cleanup_tasks.cleanup_expired_uploads")
def cleanup_expired_uploads() -> Dict[str, Any]:
    """
    Remove expired temporary uploads (runs every hour via Celery Beat).

    Finds TempUpload records where expires_at < now, deletes files
    and database records.

    Returns:
        Dict with cleanup statistics
    """
    db = SessionLocal()
    try:
        now = datetime.utcnow()

        # Find expired uploads
        expired = db.query(TempUpload).filter(TempUpload.expires_at < now).all()

        deleted_files = 0
        deleted_records = 0

        for upload in expired:
            # Delete file from storage
            if storage_service.delete_file(upload.file_path):
                deleted_files += 1

            # Delete video record if not saved
            video = db.query(Video).filter(Video.id == upload.video_id).first()
            if video and not video.is_saved:
                storage_service.delete_file(video.file_path)
                db.delete(video)

            # Delete temp upload record
            db.delete(upload)
            deleted_records += 1

        db.commit()

        return {
            "status": "completed",
            "deleted_files": deleted_files,
            "deleted_records": deleted_records,
            "checked_at": now.isoformat()
        }

    except Exception as e:
        db.rollback()
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name="app.tasks.cleanup_tasks.cleanup_orphaned_files")
def cleanup_orphaned_files() -> Dict[str, Any]:
    """
    Remove orphaned files (files on disk without DB records).

    Scans uploads directory and removes files not referenced in database.

    Returns:
        Dict with cleanup statistics
    """
    db = SessionLocal()
    try:
        import os
        from pathlib import Path
        from app.config import settings

        uploads_dir = Path(settings.UPLOAD_FOLDER)
        if not uploads_dir.exists():
            return {"status": "completed", "deleted": 0}

        # Get all file paths from DB
        videos = db.query(Video).all()
        db_paths = {video.file_path for video in videos}

        deleted = 0
        for file_path in uploads_dir.iterdir():
            if file_path.is_file() and str(file_path) not in db_paths:
                file_path.unlink()
                deleted += 1

        return {"status": "completed", "deleted": deleted}

    except Exception as e:
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()
