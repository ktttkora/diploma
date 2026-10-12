"""
Storage service for file management.

Handles saving, loading, and deleting video files and screenshots.
"""

import os
import shutil
from pathlib import Path
from typing import BinaryIO, Optional
from datetime import datetime

from app.config import settings


# Lazy storage service - directories created on first use, not at import time


class StorageService:
    """Service for managing file storage."""

    def __init__(self):
        """Initialize storage service with configured paths."""
        self.uploads_dir = Path(settings.UPLOAD_FOLDER)
        self.temp_dir = Path(settings.TEMP_FOLDER)
        self.screenshots_dir = Path(settings.SCREENSHOTS_FOLDER)
        self._initialized = False

    def _ensure_dirs(self) -> None:
        """Create directories if they don't exist (lazy)."""
        if self._initialized:
            return
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self._initialized = True

    def save_uploaded_video(self, file: BinaryIO, user_id: int, original_filename: str) -> tuple[str, int]:
        """
        Save uploaded video file.

        Args:
            file: File-like object with video data
            user_id: Owner user ID
            original_filename: Original filename from upload

        Returns:
            Tuple of (file_path, file_size)
        """
        self._ensure_dirs()
        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = self._sanitize_filename(original_filename)
        filename = f"{user_id}_{timestamp}_{safe_filename}"

        # Save file
        file_path = self.uploads_dir / filename
        file_size = 0

        with open(file_path, "wb") as f:
            while chunk := file.read(8192):
                f.write(chunk)
                file_size += len(chunk)

        return str(file_path), file_size

    def save_temp_video(self, file: BinaryIO, temp_id: str) -> tuple[str, int]:
        """
        Save temporary video file (before user confirmation).

        Args:
            file: File-like object with video data
            temp_id: Unique temporary ID

        Returns:
            Tuple of (file_path, file_size)
        """
        self._ensure_dirs()
        filename = f"temp_{temp_id}.mp4"
        file_path = self.temp_dir / filename
        file_size = 0

        with open(file_path, "wb") as f:
            while chunk := file.read(8192):
                f.write(chunk)
                file_size += len(chunk)

        return str(file_path), file_size

    def move_temp_to_uploads(self, temp_path: str, user_id: int, original_filename: str) -> str:
        """
        Move temporary file to permanent uploads directory.

        Args:
            temp_path: Path to temporary file
            user_id: Owner user ID
            original_filename: Original filename

        Returns:
            New file path in uploads directory
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = self._sanitize_filename(original_filename)
        filename = f"{user_id}_{timestamp}_{safe_filename}"

        new_path = self.uploads_dir / filename
        shutil.move(temp_path, new_path)

        return str(new_path)

    def save_screenshot(self, image_data: bytes, analysis_id: int, error_id: int, extension: str = "jpg") -> str:
        """
        Save error screenshot.

        Args:
            image_data: Image binary data
            analysis_id: Parent analysis ID
            error_id: Parent error ID
            extension: Image extension (jpg, png)

        Returns:
            Screenshot file path
        """
        self._ensure_dirs()
        filename = f"analysis_{analysis_id}_error_{error_id}.{extension}"
        file_path = self.screenshots_dir / filename

        with open(file_path, "wb") as f:
            f.write(image_data)

        # Forward slashes keep stored paths identical across Windows and Linux
        return file_path.as_posix()

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file.

        Args:
            file_path: Path to file to delete

        Returns:
            True if deleted, False if file didn't exist
        """
        path = Path(file_path)
        if path.exists():
            path.unlink()
            return True
        return False

    def delete_directory(self, dir_path: str) -> bool:
        """
        Delete a directory and all its contents.

        Args:
            dir_path: Path to directory to delete

        Returns:
            True if deleted, False if directory didn't exist
        """
        path = Path(dir_path)
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
            return True
        return False

    def get_file_size(self, file_path: str) -> Optional[int]:
        """
        Get file size in bytes.

        Args:
            file_path: Path to file

        Returns:
            File size in bytes, or None if file doesn't exist
        """
        path = Path(file_path)
        if path.exists():
            return path.stat().st_size
        return None

    def _sanitize_filename(self, filename: str) -> str:
        """
        Remove unsafe characters from filename.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Keep only alphanumeric, dots, hyphens, underscores
        safe_chars = []
        for char in filename:
            if char.isalnum() or char in ".-_":
                safe_chars.append(char)
            else:
                safe_chars.append("_")

        return "".join(safe_chars)


# Singleton instance
storage_service = StorageService()
