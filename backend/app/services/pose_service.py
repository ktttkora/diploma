"""
Pose detection service using MediaPipe.

Extracts body landmarks, detects steps, and calculates joint angles.
"""

import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, List, Any, Optional

mp_pose = mp.solutions.pose


class PoseService:
    """Service for pose detection and analysis using MediaPipe."""

    # MediaPipe landmark indices for key points
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5
    ):
        """
        Initialize pose service.

        Args:
            min_detection_confidence: Minimum confidence for pose detection
            min_tracking_confidence: Minimum confidence for pose tracking
        """
        self.min_detection = min_detection_confidence
        self.min_tracking = min_tracking_confidence

    def extract_poses_from_video(
        self,
        video_path: str,
        max_frames: Optional[int] = None,
        frame_skip: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Extract pose landmarks from all video frames.

        Args:
            video_path: Path to video file
            max_frames: Maximum frames to process (None = all)
            frame_skip: Process every Nth frame (1 = all frames)

        Returns:
            List of {frame, timestamp, landmarks, detected}

        Raises:
            RuntimeError: If video cannot be opened
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        poses = []
        frame_idx = 0
        processed = 0

        try:
            with mp_pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                min_detection_confidence=self.min_detection,
                min_tracking_confidence=self.min_tracking
            ) as pose:
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break

                    if frame_idx % frame_skip == 0:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        result = pose.process(frame_rgb)

                        if result.pose_landmarks:
                            landmarks = [
                                {
                                    "x": float(lm.x),
                                    "y": float(lm.y),
                                    "z": float(lm.z),
                                    "visibility": float(lm.visibility)
                                }
                                for lm in result.pose_landmarks.landmark
                            ]
                            poses.append({
                                "frame": frame_idx,
                                "timestamp": round(frame_idx / fps, 3),
                                "landmarks": landmarks,
                                "detected": True
                            })
                        else:
                            poses.append({
                                "frame": frame_idx,
                                "timestamp": round(frame_idx / fps, 3),
                                "landmarks": [],
                                "detected": False
                            })

                        processed += 1
                        if max_frames and processed >= max_frames:
                            break

                    frame_idx += 1
        finally:
            cap.release()

        return poses

    def detect_steps(self, poses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect dance steps from ankle movement.

        A step is detected when ankle vertical velocity exceeds threshold
        and changes direction (foot lift + placement).

        Args:
            poses: List of pose dicts from extract_poses_from_video

        Returns:
            List of {timestamp, foot, type}
        """
        steps = []
        threshold = 0.015  # Normalized coordinate movement threshold

        prev_left_y: Optional[float] = None
        prev_right_y: Optional[float] = None

        for pose in poses:
            if not pose.get("detected") or not pose.get("landmarks"):
                continue

            landmarks = pose["landmarks"]
            if len(landmarks) <= max(self.LEFT_ANKLE, self.RIGHT_ANKLE):
                continue

            left_y = landmarks[self.LEFT_ANKLE]["y"]
            right_y = landmarks[self.RIGHT_ANKLE]["y"]

            # Check left foot movement
            if prev_left_y is not None:
                if abs(left_y - prev_left_y) > threshold:
                    steps.append({
                        "timestamp": pose["timestamp"],
                        "foot": "left",
                        "type": "step"
                    })

            # Check right foot movement
            if prev_right_y is not None:
                if abs(right_y - prev_right_y) > threshold:
                    steps.append({
                        "timestamp": pose["timestamp"],
                        "foot": "right",
                        "type": "step"
                    })

            prev_left_y = left_y
            prev_right_y = right_y

        return steps

    def calculate_angles(self, landmarks: List[Dict[str, float]]) -> Dict[str, float]:
        """
        Calculate key body angles from landmarks.

        Args:
            landmarks: List of 33 landmark dicts with x, y, z

        Returns:
            Dict with spine_angle, left_knee_angle, right_knee_angle,
            left_elbow_angle, right_elbow_angle

        Raises:
            ValueError: If landmarks list is incomplete
        """
        if len(landmarks) < 33:
            raise ValueError(f"Expected 33 landmarks, got {len(landmarks)}")

        def angle(a: Dict, b: Dict, c: Dict) -> float:
            """Calculate angle at point b between points a, b, c."""
            vec1 = np.array([a["x"] - b["x"], a["y"] - b["y"]])
            vec2 = np.array([c["x"] - b["x"], c["y"] - b["y"]])
            cos_angle = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2) + 1e-8)
            return float(np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0))))

        # Spine angle (shoulder midpoint - hip midpoint vertical alignment)
        left_shoulder = landmarks[self.LEFT_SHOULDER]
        right_shoulder = landmarks[self.RIGHT_SHOULDER]
        left_hip = landmarks[self.LEFT_HIP]
        right_hip = landmarks[self.RIGHT_HIP]

        shoulder_mid = {"x": (left_shoulder["x"] + right_shoulder["x"]) / 2,
                        "y": (left_shoulder["y"] + right_shoulder["y"]) / 2}
        hip_mid = {"x": (left_hip["x"] + right_hip["x"]) / 2,
                   "y": (left_hip["y"] + right_hip["y"]) / 2}

        # Spine deviation from vertical
        dx = abs(shoulder_mid["x"] - hip_mid["x"])
        dy = abs(shoulder_mid["y"] - hip_mid["y"]) + 1e-8
        spine_angle = float(np.degrees(np.arctan(dx / dy)))

        # Knee angles
        left_knee = angle(landmarks[self.LEFT_HIP], landmarks[self.LEFT_KNEE], landmarks[self.LEFT_ANKLE])
        right_knee = angle(landmarks[self.RIGHT_HIP], landmarks[self.RIGHT_KNEE], landmarks[self.RIGHT_ANKLE])

        return {
            "spine_angle": round(spine_angle, 1),
            "left_knee_angle": round(left_knee, 1),
            "right_knee_angle": round(right_knee, 1)
        }


# Singleton instance
pose_service = PoseService()
