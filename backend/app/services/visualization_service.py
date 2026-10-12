"""
Visualization service for error screenshots.

Builds a composite image per error: the user's frame with a red skeleton
next to the reference pose with a green skeleton, plus a caption bar with
the timestamp, title, and recommendation.

Text is drawn with Pillow (see app.utils.image_text) because OpenCV's
putText cannot render Cyrillic.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import tempfile

from app.services.reference_service import reference_service
from app.services.pose_service import pose_service
from app.utils.video_utils import extract_frame
from app.utils.image_text import draw_text_block, get_font, wrap_text
from app.services.storage_service import storage_service


# MediaPipe pose connections, grouped so the skeleton reads as body parts
POSE_CONNECTIONS: List[Tuple[int, int]] = [
    # Face
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    # Torso
    (11, 12), (11, 23), (12, 24), (23, 24),
    # Left arm
    (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    # Right arm
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    # Left leg
    (23, 25), (25, 27), (27, 29), (27, 31), (29, 31),
    # Right leg
    (24, 26), (26, 28), (28, 30), (28, 32), (30, 32),
]

VISIBILITY_THRESHOLD = 0.3

# BGR colours
RED = (0, 0, 255)
GREEN = (0, 200, 0)
WHITE = (255, 255, 255)
LIGHT_GREY = (200, 200, 200)
CAPTION_BG = (32, 32, 32)
REFERENCE_BG = (240, 240, 240)


class VisualizationService:
    """Service for generating error visualization screenshots."""

    def draw_skeleton(
        self,
        image: np.ndarray,
        landmarks: List[Dict[str, float]],
        color: Tuple[int, int, int] = RED,
        thickness: int = 2,
        joint_radius: int = 3
    ) -> np.ndarray:
        """
        Draw a pose skeleton on an image.

        Args:
            image: OpenCV image in BGR order
            landmarks: List of landmark dicts with normalized x, y
            color: BGR colour for bones and joints
            thickness: Bone thickness in pixels
            joint_radius: Joint circle radius in pixels

        Returns:
            New image with the skeleton drawn
        """
        height, width = image.shape[:2]
        result = image.copy()

        for start_idx, end_idx in POSE_CONNECTIONS:
            if start_idx >= len(landmarks) or end_idx >= len(landmarks):
                continue

            start, end = landmarks[start_idx], landmarks[end_idx]

            if (start.get("visibility", 1.0) < VISIBILITY_THRESHOLD
                    or end.get("visibility", 1.0) < VISIBILITY_THRESHOLD):
                continue

            point_a = (int(start["x"] * width), int(start["y"] * height))
            point_b = (int(end["x"] * width), int(end["y"] * height))
            cv2.line(result, point_a, point_b, color, thickness, cv2.LINE_AA)

        for landmark in landmarks:
            if landmark.get("visibility", 1.0) < VISIBILITY_THRESHOLD:
                continue
            center = (int(landmark["x"] * width), int(landmark["y"] * height))
            cv2.circle(result, center, joint_radius, color, -1, cv2.LINE_AA)

        return result

    def _add_label(self, image: np.ndarray, text: str, color: Tuple[int, int, int]) -> np.ndarray:
        """
        Draw a short label in the top-left corner of an image.

        Args:
            image: OpenCV image in BGR order
            text: Label text (Latin only, drawn with OpenCV)
            color: BGR colour

        Returns:
            New image with the label
        """
        result = image.copy()
        cv2.putText(
            result, text, (12, 34),
            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 4, cv2.LINE_AA
        )
        cv2.putText(
            result, text, (12, 34),
            cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2, cv2.LINE_AA
        )
        return result

    def _build_caption(self, width: int, timestamp: float, title: str,
                       recommendation: str) -> np.ndarray:
        """
        Build the caption bar placed under the frames.

        Args:
            width: Target width in pixels
            timestamp: Error timestamp in seconds
            title: Error title
            recommendation: Fix suggestion

        Returns:
            Caption image (BGR)
        """
        caption_height = 96
        caption = np.full((caption_height, width, 3), CAPTION_BG, dtype=np.uint8)

        heading = f"{timestamp:.1f}s  {title}".strip()

        lines = [(heading, 22, WHITE)]
        if recommendation:
            font = get_font(18)
            wrapped = wrap_text(recommendation, font, width - 24)[:2]
            lines.extend((line, 18, LIGHT_GREY) for line in wrapped)

        return draw_text_block(caption, lines, padding=12, line_spacing=6)

    def create_error_screenshot(
        self,
        video_path: str,
        timestamp: float,
        error_data: Dict[str, Any],
        detected_element: Optional[str] = None
    ) -> str:
        """
        Create a composite screenshot for one error.

        Layout: the user's frame with a red skeleton, side by side with the
        reference pose in green when one is available; a caption bar with
        the timestamp, title, and recommendation sits underneath.

        Args:
            video_path: Path to the source video
            timestamp: Error timestamp in seconds
            error_data: Error details (title, recommendation, analysis_id, error_id)
            detected_element: Detected dance element, for the reference lookup

        Returns:
            Path to the saved screenshot

        Raises:
            RuntimeError: If the frame cannot be extracted or read
        """
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            user_frame_path = tmp.name

        try:
            extract_frame(video_path, timestamp, user_frame_path)
            user_frame = cv2.imread(user_frame_path)

            if user_frame is None:
                raise RuntimeError("Failed to load the extracted frame")

            # Detect the pose on this single frame. Scanning the whole video
            # here would repeat that work for every error.
            user_landmarks = pose_service.detect_pose_on_image(user_frame)

            if user_landmarks:
                user_frame = self.draw_skeleton(user_frame, user_landmarks, RED)
            user_frame = self._add_label(user_frame, "YOUR POSE", RED)

            reference_landmarks = self._find_reference_pose(
                detected_element, timestamp
            )

            if reference_landmarks:
                height, width = user_frame.shape[:2]
                reference_frame = np.full(
                    (height, width, 3), REFERENCE_BG, dtype=np.uint8
                )
                reference_frame = self.draw_skeleton(
                    reference_frame, reference_landmarks, GREEN
                )
                reference_frame = self._add_label(
                    reference_frame, "REFERENCE", GREEN
                )
                composite = np.hstack([user_frame, reference_frame])
            else:
                composite = user_frame

            caption = self._build_caption(
                composite.shape[1],
                timestamp,
                str(error_data.get("title", "Ошибка")),
                str(error_data.get("recommendation", ""))
            )

            final = np.vstack([composite, caption])

            return self._save(final, error_data)

        finally:
            Path(user_frame_path).unlink(missing_ok=True)

    def _find_reference_pose(
        self,
        detected_element: Optional[str],
        timestamp: float
    ) -> Optional[List[Dict[str, float]]]:
        """
        Look up the reference pose for an element at a timestamp.

        Args:
            detected_element: Detected dance element name
            timestamp: Error timestamp in seconds

        Returns:
            Reference landmarks, or None when no reference is available
        """
        if not detected_element:
            return None

        try:
            pose = reference_service.find_similar_pose(detected_element, timestamp)
        except Exception:
            return None

        if not pose:
            return None

        return pose.get("landmarks") or None

    def _save(self, image: np.ndarray, error_data: Dict[str, Any]) -> str:
        """
        Write the composite image through the storage service.

        Args:
            image: Final composite image (BGR)
            error_data: Must carry analysis_id and error_id

        Returns:
            Stored screenshot path

        Raises:
            RuntimeError: If the image cannot be encoded
        """
        success, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 88])
        if not success:
            raise RuntimeError("Failed to encode the screenshot")

        return storage_service.save_screenshot(
            buffer.tobytes(),
            int(error_data.get("analysis_id", 0)),
            int(error_data.get("error_id", 0))
        )


# Singleton instance
visualization_service = VisualizationService()
