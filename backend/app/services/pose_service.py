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

    def detect_steps(
        self,
        poses: List[Dict[str, Any]],
        min_interval: float = 0.25,
        min_amplitude: float = 0.03,
        max_gap: float = 0.2
    ) -> List[Dict[str, Any]]:
        """
        Detect dance steps from ankle movement.

        A step is one swing of the foot. The ankle rises during the lift and
        starts falling again at the top of that swing, so the step is
        recorded at that turning point: the end of the lift, where the foot
        begins to come down. Detecting the turning point instead of each
        frame of movement gives one step per physical step, no matter how
        long the swing lasts or what the frame rate is.

        Amplitude is accumulated in normalised coordinates, so the result
        does not depend on the video's frame rate. min_interval is only a
        debounce against a foot flapping back and forth from tracking noise.

        The exact phase relative to the music is not calibrated: the turning
        point sits slightly before the foot lands, and matching that to a
        beat needs real footage with a known beat to check against.

        Args:
            poses: List of pose dicts from extract_poses_from_video
            min_interval: Minimum time between two steps in seconds
            min_amplitude: Minimum swing size (normalised units) to count as a step
            max_gap: Reset tracking state when frames are further apart than this

        Returns:
            List of {timestamp, foot, type}
        """
        NOISE = 0.002  # Ignore sub-pixel jitter in the landmarks
        LIFT = -1      # Ankle moving up the frame (y decreasing)
        PLACE = 1      # Ankle moving down the frame (y increasing)

        steps: List[Dict[str, Any]] = []
        prev_y: Dict[str, Optional[float]] = {"left": None, "right": None}
        direction: Dict[str, int] = {"left": 0, "right": 0}
        amplitude: Dict[str, float] = {"left": 0.0, "right": 0.0}
        prev_timestamp: Optional[float] = None
        last_step_time: Optional[float] = None

        def reset_tracking() -> None:
            """Drop per-foot state so a gap is not credited to one step."""
            prev_y["left"] = prev_y["right"] = None
            direction["left"] = direction["right"] = 0
            amplitude["left"] = amplitude["right"] = 0.0

        for pose in poses:
            # A frame without a pose breaks the motion chain
            if not pose.get("detected") or not pose.get("landmarks"):
                reset_tracking()
                prev_timestamp = None
                continue

            landmarks = pose["landmarks"]
            if len(landmarks) <= max(self.LEFT_ANKLE, self.RIGHT_ANKLE):
                continue

            timestamp = pose["timestamp"]

            # A long gap makes the movement between frames unreliable
            if prev_timestamp is not None and timestamp - prev_timestamp > max_gap:
                reset_tracking()

            turning: Dict[str, float] = {}

            for foot, index in (("left", self.LEFT_ANKLE),
                                ("right", self.RIGHT_ANKLE)):
                y = landmarks[index]["y"]

                if prev_y[foot] is None:
                    prev_y[foot] = y
                    continue

                delta = y - prev_y[foot]
                prev_y[foot] = y

                if abs(delta) < NOISE:
                    continue

                sign = PLACE if delta > 0 else LIFT

                if direction[foot] == 0 or sign == direction[foot]:
                    # Still moving the same way; keep accumulating the swing
                    direction[foot] = sign
                    amplitude[foot] += abs(delta)
                    continue

                # Direction reversed. Only the top of the swing ends a step;
                # the bottom is the foot resting and starting its next lift.
                if direction[foot] == LIFT and amplitude[foot] >= min_amplitude:
                    turning[foot] = amplitude[foot]

                direction[foot] = sign
                amplitude[foot] = abs(delta)

            prev_timestamp = timestamp

            if not turning:
                continue

            # Debounce: a foot flapping from noise is one step, not several
            if (last_step_time is not None
                    and timestamp - last_step_time < min_interval):
                continue

            # Both feet can turn in one frame; attribute the step to the
            # foot that swung further
            foot = max(turning, key=lambda f: turning[f])
            steps.append({
                "timestamp": timestamp,
                "foot": foot,
                "type": "step"
            })
            last_step_time = timestamp

        return steps

    def detect_pose_on_image(self, image: np.ndarray) -> Optional[List[Dict[str, float]]]:
        """
        Detect a pose on a single image.

        Used when only one moment matters (for example drawing a skeleton
        on an error screenshot). Far cheaper than scanning a whole video.

        Args:
            image: OpenCV image in BGR order

        Returns:
            List of 33 landmark dicts, or None if no pose was found
        """
        if image is None or image.size == 0:
            return None

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        with mp_pose.Pose(
            static_image_mode=True,
            model_complexity=1,
            min_detection_confidence=self.min_detection
        ) as pose:
            result = pose.process(image_rgb)

            if not result.pose_landmarks:
                return None

            return [
                {
                    "x": float(lm.x),
                    "y": float(lm.y),
                    "z": float(lm.z),
                    "visibility": float(lm.visibility)
                }
                for lm in result.pose_landmarks.landmark
            ]

    def find_pose_at(
        self,
        poses: List[Dict[str, Any]],
        timestamp: float,
        tolerance: float = 0.5
    ) -> Optional[List[Dict[str, float]]]:
        """
        Find the detected pose closest to a timestamp.

        Args:
            poses: Poses from extract_poses_from_video
            timestamp: Target timestamp in seconds
            tolerance: Maximum distance in seconds

        Returns:
            Landmarks of the closest detected pose, or None
        """
        best: Optional[Dict[str, Any]] = None
        best_distance = tolerance

        for pose in poses:
            if not pose.get("detected") or not pose.get("landmarks"):
                continue
            distance = abs(pose["timestamp"] - timestamp)
            if distance <= best_distance:
                best = pose
                best_distance = distance

        return best["landmarks"] if best else None

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
