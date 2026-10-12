"""
Visualization service for error screenshots.

Generates composite screenshots: original frame + pose skeleton overlay
showing user's pose vs reference pose.
"""

import cv2
import numpy as np
import mediapipe as mp
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from app.services.reference_service import reference_service
from app.services.pose_service import pose_service
from app.utils.video_utils import extract_frame
from app.services.storage_service import storage_service


# MediaPipe pose connections for skeleton drawing
POSE_CONNECTIONS = [
    # Face
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    # Torso
    (11, 12), (11, 23), (12, 24), (23, 24),
    (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (23, 25), (25, 27), (27, 29), (27, 31), (29, 31),
    (24, 26), (26, 28), (28, 30), (28, 32), (30, 32),
]


class VisualizationService:
    """Service for generating error visualization screenshots."""

    def __init__(self):
        """Initialize visualization service."""
        pass

    def draw_skeleton(
        self,
        image: np.ndarray,
        landmarks: List[Dict[str, float]],
        color: Tuple[int, int, int] = (0, 0, 255),
        thickness: int = 2
    ) -> np.ndarray:
        """
        Draw pose skeleton on image.

        Args:
            image: OpenCV image (BGR)
            landmarks: List of 33 landmark dicts with x, y (normalized)
            color: BGR color tuple
            thickness: Line thickness

        Returns:
            Image with skeleton overlay
        """
        h, w = image.shape[:2]
        result = image.copy()

        # Draw connections
        for start_idx, end_idx in POSE_CONNECTIONS:
            if start_idx < len(landmarks) and end_idx < len(landmarks):
                start = landmarks[start_idx]
                end = landmarks[end_idx]

                # Skip low-visibility points
                if start.get("visibility", 1.0) < 0.3 or end.get("visibility", 1.0) < 0.3:
                    continue

                x1, y1 = int(start["x"] * w), int(start["y"] * h)
                x2, y2 = int(end["x"] * w), int(end["y"] * h)

                cv2.line(result, (x1, y1), (x2, y2), color, thickness)

        # Draw joint points
        for lm in landmarks:
            if lm.get("visibility", 1.0) < 0.3:
                continue
            x, y = int(lm["x"] * w), int(lm["y"] * h)
            cv2.circle(result, (x, y), 3, color, -1)

        return result

    def create_error_screenshot(
        self,
        video_path: str,
        timestamp: float,
        error_data: Dict[str, Any],
        detected_element: Optional[str] = None
    ) -> str:
        """
        Create composite error screenshot.

        Layout: [User frame with RED skeleton] | [Reference frame with GREEN skeleton]
        If no reference available: single frame with red skeleton + text overlay.

        Args:
            video_path: Path to source video
            timestamp: Timestamp of error in seconds
            error_data: Error details (title, description, recommendation)
            detected_element: Name of detected dance element (for reference lookup)

        Returns:
            Path to saved screenshot

        Raises:
            RuntimeError: If frame extraction or processing fails
        """
        import tempfile

        # 1. Extract user frame
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            user_frame_path = tmp.name

        try:
            extract_frame(video_path, timestamp, user_frame_path)
            user_frame = cv2.imread(user_frame_path)
            if user_frame is None:
                raise RuntimeError("Failed to load extracted frame")

            # 2. Detect user pose on this frame
            poses = pose_service.extract_poses_from_video(video_path)
            user_landmarks = None
            for pose in poses:
                if abs(pose["timestamp"] - timestamp) < 0.5 and pose.get("detected"):
                    user_landmarks = pose["landmarks"]
                    break

            # Draw red skeleton on user frame
            if user_landmarks:
                user_frame = self.draw_skeleton(user_frame, user_landmarks, color=(0, 0, 255))

            # 3. Try to get reference pose
            ref_landmarks = None
            if detected_element:
                ratio = None  # Use timestamp matching
                ref_pose = reference_service.find_similar_pose(detected_element, timestamp)
                if ref_pose:
                    ref_landmarks = ref_pose.get("landmarks", [])

            if ref_landmarks:
                # Create reference visualization (blank background + green skeleton)
                h, w = user_frame.shape[:2]
                ref_frame = np.ones((h, w, 3), dtype=np.uint8) * 240  # Light gray
                ref_frame = self.draw_skeleton(ref_frame, ref_landmarks, color=(0, 255, 0))

                # Add labels
                cv2.putText(ref_frame, "REFERENCE", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 150, 0), 2)
                cv2.putText(user_frame, "YOUR POSE", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 200), 2)

                # Combine side by side
                composite = np.hstack([user_frame, ref_frame])
            else:
                # Single frame with red skeleton
                cv2.putText(user_frame, "YOUR POSE", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 200), 2)
                composite = user_frame

            # 4. Add error text at bottom
            text_height = 80
            h, w = composite.shape[:2]
            text_bar = np.ones((text_height, w, 3), dtype=np.uint8) * 30  # Dark bar

            title = error_data.get("title", "Error")
            recommendation = error_data.get("recommendation", "")

            cv2.putText(text_bar, f"{timestamp:.1f}s: {title}", (10, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            # Truncate recommendation to fit
            rec_short = recommendation[:100] + "..." if len(recommendation) > 100 else recommendation
            cv2.putText(text_bar, rec_short, (10, 55),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            final = np.vstack([composite, text_bar])

            # 5. Save via storage service
            import uuid
            temp_output = str(Path(tempfile.gettempdir()) / f"screenshot_{uuid.uuid4().hex[:8]}.jpg")
            cv2.imwrite(temp_output, final)

            with open(temp_output, "rb") as f:
                image_data = f.read()

            # Clean temp file
            Path(temp_output).unlink(missing_ok=True)

            # Save to permanent location
            analysis_id = error_data.get("analysis_id", 0)
            error_id = error_data.get("error_id", 0)
            screenshot_path = storage_service.save_screenshot(
                image_data, analysis_id, error_id
            )

            return screenshot_path

        finally:
            Path(user_frame_path).unlink(missing_ok=True)


# Singleton instance
visualization_service = VisualizationService()
