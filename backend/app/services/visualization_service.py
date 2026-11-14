"""
Visualization service for error screenshots.

Builds a composite image per error: the user's frame with one red
skeleton, and the catalog pose in green beside it when the shapes match.
The written remark stays on the result card, not on the picture.

Text is drawn with Pillow (see app.utils.image_text) because OpenCV's
putText cannot render Cyrillic.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import tempfile

from app.services.reference_service import reference_service
from app.services.pose_service import choose_pose, pose_service
from app.utils.video_utils import extract_frame
from app.utils.image_text import draw_text_block
from app.services.storage_service import storage_service


# MediaPipe pose connections, grouped so the skeleton reads as body parts
POSE_CONNECTIONS: List[Tuple[int, int]] = [
    # Face
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    # Torso and neck. Ears join the shoulders so the head is not a separate blob.
    (11, 12), (11, 23), (12, 24), (23, 24),
    (0, 11), (0, 12),
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

# BGR colours. One dancer is one colour: the user is red, the reference is green.
RED = (0, 0, 255)
GREEN = (0, 200, 0)
WHITE = (255, 255, 255)
REFERENCE_BG = (240, 240, 240)

PERSON_LABEL = {"female": "Девушка", "male": "Мужчина"}


class VisualizationService:
    """Service for generating error visualization screenshots."""

    def draw_skeleton(
        self,
        image: np.ndarray,
        landmarks: List[Dict[str, float]],
        color: Tuple[int, int, int] = RED,
        thickness: int = 2,
        joint_radius: int = 3,
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

    def _with_title(
        self,
        image: np.ndarray,
        text: str,
        color: Tuple[int, int, int],
        background: Tuple[int, int, int],
    ) -> np.ndarray:
        """Put a one-line title above the frame so it does not cover the body."""
        strip = np.full((46, image.shape[1], 3), background, dtype=np.uint8)
        strip = draw_text_block(
            strip, [(text, 24, color)], padding=8, background=background
        )
        return np.vstack([strip, image])

    def _fit_landmarks(
        self,
        landmarks: List[Dict[str, float]],
        panel_width: int,
        panel_height: int,
        aspect: float,
    ) -> List[Dict[str, float]]:
        """
        Place a catalog pose in the panel without stretching it.

        Landmark x and y are fractions of a video frame. A wide frame makes
        an upright body look narrow if those fractions are drawn on a tall crop.
        """
        visible = [
            landmark for landmark in landmarks
            if landmark.get("visibility", 1.0) >= VISIBILITY_THRESHOLD
        ]
        if len(visible) < 3 or panel_width < 2 or panel_height < 2:
            return landmarks
        points = [
            (float(landmark["x"]) * aspect, float(landmark["y"]))
            for landmark in visible
        ]
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        span_x = max(max(xs) - min(xs), 1e-3)
        span_y = max(max(ys) - min(ys), 1e-3)
        center_x = (min(xs) + max(xs)) / 2
        center_y = (min(ys) + max(ys)) / 2
        scale = min(panel_width * 0.82 / span_x, panel_height * 0.82 / span_y)
        fitted = []
        for landmark in landmarks:
            px = float(landmark["x"]) * aspect
            py = float(landmark["y"])
            fitted.append({
                **landmark,
                "x": 0.5 + (px - center_x) * scale / panel_width,
                "y": 0.5 + (py - center_y) * scale / panel_height,
            })
        return fitted

    def create_error_screenshot(
        self,
        video_path: str,
        timestamp: float,
        error_data: Dict[str, Any],
        detected_element: Optional[str] = None
    ) -> str:
        """
        Create a composite screenshot for one error.

        Layout: the user's frame with one red skeleton. When a catalog pose
        has the same shape, its green skeleton sits beside the photo.
        The remark and the fix stay on the card above the picture.

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

            title = str(error_data.get("title", "Ошибка"))
            description = str(error_data.get("description", ""))
            note = f"{title}. {description}"
            person = str(error_data.get("person") or "")
            label = PERSON_LABEL.get(person, "Поза")
            poses = pose_service.detect_poses_on_image(user_frame)
            user_landmarks = choose_pose(
                poses,
                error_data.get("anchor_x"),
                error_data.get("anchor_y"),
                note,
                person=person or None,
                image=user_frame,
            )
            # Match the catalog on the original pose. The close-up crop
            # stretches x and y differently and would hide a real match.
            reference_landmarks = None
            if user_landmarks:
                reference_landmarks = self._find_reference_pose(
                    detected_element, user_landmarks
                )
            if user_landmarks:
                # Arms are left out of the box so a hand on the partner
                # does not pull him into the close-up.
                user_frame, user_landmarks = self._crop_to_pose(
                    user_frame,
                    user_landmarks,
                    indices=tuple(range(0, 13)) + tuple(range(23, 33)),
                )
                thickness = max(2, user_frame.shape[1] // 180)
                user_frame = self.draw_skeleton(
                    user_frame,
                    user_landmarks,
                    RED,
                    thickness=thickness,
                    joint_radius=max(3, thickness),
                )

            reference_frame = None
            if reference_landmarks:
                height, width = user_frame.shape[:2]
                reference_frame = np.full(
                    (height, width, 3), REFERENCE_BG, dtype=np.uint8
                )
                reference_frame = self.draw_skeleton(
                    reference_frame,
                    self._fit_landmarks(
                        reference_landmarks,
                        width,
                        height,
                        self._reference_aspect(detected_element),
                    ),
                    GREEN,
                    thickness=max(2, width // 140),
                    joint_radius=max(3, width // 140),
                )

            if reference_frame is not None:
                user_frame = self._with_title(user_frame, label, WHITE, (20, 20, 20))
                reference_frame = self._with_title(
                    reference_frame, "Как надо", (0, 90, 0), (255, 255, 255)
                )
                if reference_frame.shape[0] != user_frame.shape[0]:
                    target = max(reference_frame.shape[0], user_frame.shape[0])
                    def pad(image: np.ndarray, fill: Tuple[int, int, int]) -> np.ndarray:
                        extra = target - image.shape[0]
                        if extra <= 0:
                            return image
                        return cv2.copyMakeBorder(
                            image, 0, extra, 0, 0, cv2.BORDER_CONSTANT, value=fill
                        )
                    user_frame = pad(user_frame, (20, 20, 20))
                    reference_frame = pad(reference_frame, REFERENCE_BG)
                final = np.hstack([user_frame, reference_frame])
            else:
                final = user_frame

            return self._save(final, error_data)

        finally:
            Path(user_frame_path).unlink(missing_ok=True)

    def _crop_to_pose(
        self,
        image: np.ndarray,
        landmarks: List[Dict[str, float]],
        pad_ratio: float = 0.35,
        indices: Optional[Tuple[int, ...]] = None,
    ) -> Tuple[np.ndarray, List[Dict[str, float]]]:
        """
        Cut the frame down to the chosen dancer and rescale landmarks to it.

        A full-room frame makes the fault hard to see. The crop keeps the
        whole body, including a raised leg.
        """
        height, width = image.shape[:2]
        xs = []
        ys = []
        allowed = set(indices) if indices is not None else None
        for index, landmark in enumerate(landmarks):
            if allowed is not None and index not in allowed:
                continue
            if landmark.get("visibility", 1.0) < VISIBILITY_THRESHOLD:
                continue
            xs.append(float(landmark["x"]))
            ys.append(float(landmark["y"]))
        if not xs or not ys:
            return image, landmarks

        x0 = max(0.0, min(xs) - pad_ratio * (max(xs) - min(xs) + 0.05))
        x1 = min(1.0, max(xs) + pad_ratio * (max(xs) - min(xs) + 0.05))
        y0 = max(0.0, min(ys) - pad_ratio * (max(ys) - min(ys) + 0.05))
        y1 = min(1.0, max(ys) + pad_ratio * (max(ys) - min(ys) + 0.05))
        left, right = int(x0 * width), max(int(x1 * width), int(x0 * width) + 2)
        top, bottom = int(y0 * height), max(int(y1 * height), int(y0 * height) + 2)
        right = min(right, width)
        bottom = min(bottom, height)
        crop_w = right - left
        crop_h = bottom - top
        if crop_w < 2 or crop_h < 2:
            return image, landmarks

        cropped = image[top:bottom, left:right]
        rescaled = []
        for landmark in landmarks:
            rescaled.append({
                **landmark,
                "x": (float(landmark["x"]) * width - left) / crop_w,
                "y": (float(landmark["y"]) * height - top) / crop_h,
            })
        return cropped, rescaled

    def _reference_aspect(self, element_name: Optional[str]) -> float:
        """Width divided by height of the catalog clip. Wide video is above 1."""
        if not element_name:
            return 16 / 9
        data = reference_service.get_reference(element_name) or {}
        try:
            width = float(data.get("width") or 0)
            height = float(data.get("height") or 0)
        except (TypeError, ValueError):
            width = height = 0.0
        if width > 0 and height > 0:
            return width / height
        return 16 / 9

    def _find_reference_pose(
        self,
        detected_element: Optional[str],
        landmarks: List[Dict[str, float]],
    ) -> Optional[List[Dict[str, float]]]:
        """
        Look up a reference pose with a similar shape.

        Returns None when the element is unknown or the closest catalog pose
        is a different movement.
        """
        if not detected_element or not landmarks:
            return None

        try:
            return reference_service.find_pose_like(detected_element, landmarks)
        except Exception:
            return None

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
