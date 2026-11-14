"""
Pose detection service using MediaPipe.

Extracts body landmarks, detects steps, and calculates joint angles.
"""

from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, List, Any, Optional, Tuple

mp_pose = mp.solutions.pose

# Second detector. The pose solution returns one body and, on a close
# hold, both of its passes can land on the same dancer. This file is
# downloaded once; if it is missing, the solution loop still runs.
LANDMARKER_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "models" / "pose_landmarker_lite.task"
)
# A white top against a black shirt. The patch can catch the partner,
# so the gap is smaller than a clean chest sample.
BRIGHTNESS_GAP = 60
FEMALE_DARK_LIMIT = 60
MALE_LIGHT_LIMIT = 160

# Torso and feet used to tell two dancers apart. Arms are left out of the
# mask so an extended hand does not hide the partner.
TORSO_LANDMARKS = (11, 12, 23, 24)
FOOT_LANDMARKS = (27, 28, 29, 30, 31, 32)
MASK_LANDMARKS = tuple(range(0, 13)) + tuple(range(23, 33))
COMPARE_LANDMARKS = (11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28)


def torso_center(landmarks: List[Dict[str, float]]) -> Optional[Tuple[float, float]]:
    """Return the mean of the visible shoulders and hips, or None."""
    points = []
    for index in TORSO_LANDMARKS:
        if index >= len(landmarks):
            continue
        landmark = landmarks[index]
        if landmark.get("visibility", 1.0) < 0.3:
            continue
        points.append((float(landmark["x"]), float(landmark["y"])))
    if len(points) < 2:
        return None
    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )


def raised_foot(landmarks: List[Dict[str, float]]) -> Optional[float]:
    """Return the highest visible foot y. Smaller means higher in the frame."""
    heights = []
    for index in FOOT_LANDMARKS:
        if index >= len(landmarks):
            continue
        landmark = landmarks[index]
        if landmark.get("visibility", 1.0) < 0.3:
            continue
        heights.append(float(landmark["y"]))
    if not heights:
        return None
    return min(heights)


def leg_lift(landmarks: List[Dict[str, float]]) -> Optional[float]:
    """How far the higher knee sits above the hips. Positive means a raised leg."""
    hips = []
    knees = []
    for index in (23, 24):
        if index < len(landmarks) and landmarks[index].get("visibility", 1.0) >= 0.3:
            hips.append(float(landmarks[index]["y"]))
    for index in (25, 26):
        if index < len(landmarks) and landmarks[index].get("visibility", 1.0) >= 0.3:
            knees.append(float(landmarks[index]["y"]))
    if not hips or not knees:
        return None
    hip_y = sum(hips) / len(hips)
    return hip_y - min(knees)


def mentions_raised_leg(text: str) -> bool:
    """Whether the error text describes a kick or a lifted leg."""
    lowered = (text or "").lower()
    if "удар" in lowered or "мах" in lowered:
        return True
    return "ног" in lowered and any(
        word in lowered for word in ("высок", "поднят", "вверх")
    )


def mentions_deep_sit(text: str) -> bool:
    """Whether the error text describes a lunge or a drop into the hip."""
    lowered = (text or "").lower()
    return any(word in lowered for word in ("садит", "выпад", "бедр", "провал"))


def stance_width(landmarks: List[Dict[str, float]]) -> Optional[float]:
    """Horizontal distance between the ankles. Wider means a longer lunge."""
    if len(landmarks) <= 28:
        return None
    left, right = landmarks[27], landmarks[28]
    if left.get("visibility", 1.0) < 0.3 or right.get("visibility", 1.0) < 0.3:
        return None
    return abs(float(left["x"]) - float(right["x"]))


def torso_brightness(image: np.ndarray, landmarks: List[Dict[str, float]]) -> Optional[float]:
    """Mean brightness of a small patch on the chest, from 0 to 255."""
    center = torso_center(landmarks)
    if center is None or image is None or image.size == 0:
        return None
    height, width = image.shape[:2]
    x = min(max(int(center[0] * width), 0), width - 1)
    y = min(max(int(center[1] * height), 0), height - 1)
    patch = image[max(0, y - 12):y + 12, max(0, x - 12):x + 12]
    if patch.size == 0:
        return None
    return float(patch.mean())


def same_dancer(
    left: List[Dict[str, float]],
    right: List[Dict[str, float]],
    image: Optional[np.ndarray] = None,
) -> bool:
    """
    Whether two detections are the same dancer.

    Close chests usually are. A large brightness gap keeps both: in a
    hold the two torso estimates can sit near each other while the
    clothes are different.
    """
    left_center = torso_center(left)
    right_center = torso_center(right)
    if left_center is None or right_center is None:
        return False
    distance = (
        (left_center[0] - right_center[0]) ** 2
        + (left_center[1] - right_center[1]) ** 2
    ) ** 0.5
    if distance >= 0.12:
        return False
    if image is not None and distance >= 0.05:
        left_value = torso_brightness(image, left)
        right_value = torso_brightness(image, right)
        if (
            left_value is not None
            and right_value is not None
            and abs(left_value - right_value) >= BRIGHTNESS_GAP
        ):
            return False
    return True


def choose_pose(
    poses: List[List[Dict[str, float]]],
    anchor_x: Optional[float] = None,
    anchor_y: Optional[float] = None,
    text: str = "",
    person: Optional[str] = None,
    image: Optional[np.ndarray] = None,
) -> Optional[List[Dict[str, float]]]:
    """
    Pick the dancer the error is about.

    An anchor is the chest point from the vision model. Without one, a
    clear clothing gap wins: the lighter chest is the woman and the darker
    is the man. A kick then selects the higher foot, and a lunge selects
    the wider stance. Detection order is not used: the first body is not
    a gender. One pose in clothes that contradict the requested person is
    left undrawn.
    """
    if not poses:
        return None

    if anchor_x is not None and anchor_y is not None:
        ranked = []
        for pose in poses:
            center = torso_center(pose)
            if center is None:
                continue
            distance = ((center[0] - anchor_x) ** 2 + (center[1] - anchor_y) ** 2) ** 0.5
            ranked.append((distance, pose))
        if not ranked:
            return None
        ranked.sort(key=lambda item: item[0])
        if ranked[0][0] > 0.45:
            return None
        return ranked[0][1]

    if image is not None and person in ("female", "male") and len(poses) >= 2:
        lights = []
        for pose in poses:
            value = torso_brightness(image, pose)
            if value is not None:
                lights.append((value, pose))
        lights.sort(key=lambda item: item[0])
        if len(lights) >= 2 and lights[-1][0] - lights[0][0] >= BRIGHTNESS_GAP:
            return lights[-1][1] if person == "female" else lights[0][1]

    if mentions_raised_leg(text):
        feet = []
        for pose in poses:
            height = raised_foot(pose)
            if height is not None:
                feet.append((height, pose))
        feet.sort(key=lambda item: item[0])
        if len(feet) >= 2 and feet[1][0] - feet[0][0] >= 0.08:
            return feet[0][1]
        lifts = []
        for pose in poses:
            lift = leg_lift(pose)
            if lift is not None:
                lifts.append((lift, pose))
        lifts.sort(key=lambda item: item[0], reverse=True)
        if len(lifts) >= 2 and lifts[0][0] - lifts[1][0] >= 0.08:
            return lifts[0][1]
        if len(feet) == 1 and feet[0][0] < 0.55:
            return feet[0][1]
        if len(poses) == 1:
            return None

    if person == "female" and mentions_deep_sit(text):
        widths = []
        for pose in poses:
            width = stance_width(pose)
            if width is not None:
                widths.append((width, pose))
        widths.sort(key=lambda item: item[0], reverse=True)
        if len(widths) >= 2 and widths[0][0] - widths[1][0] >= 0.06:
            return widths[0][1]

    if len(poses) == 1:
        if image is not None and person in ("female", "male"):
            value = torso_brightness(image, poses[0])
            if person == "female" and value is not None and value < FEMALE_DARK_LIMIT:
                return None
            if person == "male" and value is not None and value > MALE_LIGHT_LIMIT:
                return None
        return poses[0]
    return None


def pose_distance(
    left: List[Dict[str, float]],
    right: List[Dict[str, float]],
) -> Optional[float]:
    """
    Compare two poses after centering on the hips and scaling by the torso.

    Returns the root-mean-square joint distance in torso lengths, or None
    when too few joints are visible to compare.
    """
    def points(landmarks: List[Dict[str, float]]) -> Dict[int, Tuple[float, float]]:
        found = {}
        for index in COMPARE_LANDMARKS:
            if index >= len(landmarks):
                continue
            landmark = landmarks[index]
            if landmark.get("visibility", 1.0) < 0.3:
                continue
            found[index] = (float(landmark["x"]), float(landmark["y"]))
        return found

    def frame(joints: Dict[int, Tuple[float, float]]):
        hips = [joints[index] for index in (23, 24) if index in joints]
        shoulders = [joints[index] for index in (11, 12) if index in joints]
        if not hips or not shoulders:
            return None
        hip_x = sum(point[0] for point in hips) / len(hips)
        hip_y = sum(point[1] for point in hips) / len(hips)
        shoulder_x = sum(point[0] for point in shoulders) / len(shoulders)
        shoulder_y = sum(point[1] for point in shoulders) / len(shoulders)
        scale = ((shoulder_x - hip_x) ** 2 + (shoulder_y - hip_y) ** 2) ** 0.5
        if scale < 1e-3:
            return None
        return hip_x, hip_y, scale

    left_points = points(left)
    right_points = points(right)
    shared = [index for index in COMPARE_LANDMARKS if index in left_points and index in right_points]
    if len(shared) < 6:
        return None
    left_frame = frame(left_points)
    right_frame = frame(right_points)
    if left_frame is None or right_frame is None:
        return None

    total = 0.0
    for index in shared:
        lx = (left_points[index][0] - left_frame[0]) / left_frame[2]
        ly = (left_points[index][1] - left_frame[1]) / left_frame[2]
        rx = (right_points[index][0] - right_frame[0]) / right_frame[2]
        ry = (right_points[index][1] - right_frame[1]) / right_frame[2]
        total += (lx - rx) ** 2 + (ly - ry) ** 2
    return (total / len(shared)) ** 0.5


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
        self._landmarker = None
        self._landmarker_loaded = False

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

    def _detect_raw(
        self,
        image: np.ndarray,
        min_detection: float,
    ) -> Optional[List[Dict[str, float]]]:
        """Run one static MediaPipe pass. Coordinates stay in this image."""
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        with mp_pose.Pose(
            static_image_mode=True,
            model_complexity=1,
            min_detection_confidence=min_detection,
        ) as pose:
            result = pose.process(image_rgb)
            if not result.pose_landmarks:
                return None
            return [
                {
                    "x": float(lm.x),
                    "y": float(lm.y),
                    "z": float(lm.z),
                    "visibility": float(lm.visibility),
                }
                for lm in result.pose_landmarks.landmark
            ]

    def detect_pose_on_image(self, image: np.ndarray) -> Optional[List[Dict[str, float]]]:
        """
        Detect the most prominent pose on a single image.

        Args:
            image: OpenCV image in BGR order

        Returns:
            List of 33 landmark dicts, or None if no pose was found
        """
        if image is None or image.size == 0:
            return None
        return self._detect_raw(image, self.min_detection)

    def detect_poses_on_image(
        self,
        image: np.ndarray,
        max_people: int = 3,
    ) -> List[List[Dict[str, float]]]:
        """
        Detect up to max_people poses.

        The pose solution returns one body. Each found body is masked and
        the search repeats. A second model can see the partner the mask
        loop folds into the first dancer. Poses whose chests lie on the
        same clothes are kept once.
        """
        if image is None or image.size == 0:
            return []

        height, width = image.shape[:2]
        found: List[List[Dict[str, float]]] = []

        def keep(landmarks: Optional[List[Dict[str, float]]]) -> None:
            if not landmarks or torso_center(landmarks) is None:
                return
            if any(same_dancer(landmarks, previous, image) for previous in found):
                return
            if len(found) >= max_people:
                return
            found.append(landmarks)

        for landmarks in self._detect_landmarker(image):
            keep(landmarks)

        blocked = np.zeros((height, width), dtype=np.uint8)
        for _ in range(max_people):
            working = image.copy()
            working[blocked > 0] = (40, 40, 40)
            landmarks = self._detect_raw(working, 0.35)
            if not landmarks:
                break
            center = torso_center(landmarks)
            if center is None:
                break
            cx = min(max(int(center[0] * width), 0), width - 1)
            cy = min(max(int(center[1] * height), 0), height - 1)
            duplicate = any(same_dancer(landmarks, previous, image) for previous in found)
            # A painted pixel can belong to the partner in a close hold.
            # Stop only when the same dancer is found again under the mask.
            if blocked[cy, cx] and duplicate:
                break
            if not duplicate:
                keep(landmarks)
            self._paint_mask(blocked, landmarks)

        return [self._refine_pose(image, pose) for pose in found]

    def _detect_landmarker(self, image: np.ndarray) -> List[List[Dict[str, float]]]:
        """Up to two poses from the task model. Empty when the file is absent."""
        landmarker = self._pose_landmarker()
        if landmarker is None:
            return []
        rgb = np.ascontiguousarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        try:
            result = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        except Exception:
            return []
        poses = []
        for people in result.pose_landmarks or []:
            poses.append([
                {
                    "x": float(landmark.x),
                    "y": float(landmark.y),
                    "z": float(landmark.z),
                    "visibility": float(landmark.visibility or 1.0),
                }
                for landmark in people
            ])
        return poses

    def _pose_landmarker(self):
        """Load the multi-person model once. None when the file is missing."""
        if self._landmarker_loaded:
            return self._landmarker
        self._landmarker_loaded = True
        if not LANDMARKER_PATH.is_file():
            return None
        try:
            from mediapipe.tasks import python as mp_tasks
            from mediapipe.tasks.python import vision

            options = vision.PoseLandmarkerOptions(
                base_options=mp_tasks.BaseOptions(model_asset_path=str(LANDMARKER_PATH)),
                running_mode=vision.RunningMode.IMAGE,
                num_poses=2,
                min_pose_detection_confidence=0.25,
            )
            self._landmarker = vision.PoseLandmarker.create_from_options(options)
        except Exception:
            self._landmarker = None
        return self._landmarker

    def _refine_pose(
        self,
        image: np.ndarray,
        landmarks: List[Dict[str, float]],
    ) -> List[Dict[str, float]]:
        """
        Re-detect one dancer inside a crop.

        The second pass on a masked full frame often bends a raised leg.
        A crop where that dancer fills the picture gives a cleaner skeleton.
        """
        height, width = image.shape[:2]
        center = torso_center(landmarks)
        if center is None:
            return landmarks

        xs = [float(lm["x"]) for lm in landmarks if lm.get("visibility", 1.0) >= 0.3]
        ys = [float(lm["y"]) for lm in landmarks if lm.get("visibility", 1.0) >= 0.3]
        if not xs or not ys:
            return landmarks

        span_x = max(max(xs) - min(xs), 0.18)
        span_y = max(max(ys) - min(ys), 0.35)
        x0 = max(0.0, center[0] - span_x * 0.75)
        x1 = min(1.0, center[0] + span_x * 0.75)
        y0 = max(0.0, min(ys) - span_y * 0.15)
        y1 = min(1.0, max(ys) + span_y * 0.2)
        left, right = int(x0 * width), int(x1 * width)
        top, bottom = int(y0 * height), int(y1 * height)
        if right - left < 40 or bottom - top < 40:
            return landmarks

        refined = self._detect_raw(image[top:bottom, left:right], 0.35)
        if not refined:
            return landmarks

        crop_w = right - left
        crop_h = bottom - top
        mapped = []
        for landmark in refined:
            mapped.append({
                **landmark,
                "x": (float(landmark["x"]) * crop_w + left) / width,
                "y": (float(landmark["y"]) * crop_h + top) / height,
            })
        refined_center = torso_center(mapped)
        if refined_center is None:
            return landmarks
        shift = (
            (refined_center[0] - center[0]) ** 2
            + (refined_center[1] - center[1]) ** 2
        ) ** 0.5
        if shift > 0.18:
            return landmarks
        # A crop of two overlapping dancers can lock onto the partner.
        # Keep the first skeleton when the chest colour jumps.
        before = torso_brightness(image, landmarks)
        after = torso_brightness(image, mapped)
        if before is not None and after is not None and abs(before - after) >= 50:
            return landmarks
        return mapped

    def _same_person(
        self,
        left: List[Dict[str, float]],
        right: List[Dict[str, float]],
    ) -> bool:
        """Whether two detections are the same dancer seen again."""
        return same_dancer(left, right)

    def _paint_mask(self, mask: np.ndarray, landmarks: List[Dict[str, float]]) -> None:
        """Mark a dancer's torso, head and legs so the next pass skips them."""
        height, width = mask.shape[:2]
        points = []
        for index in MASK_LANDMARKS:
            if index >= len(landmarks):
                continue
            landmark = landmarks[index]
            if landmark.get("visibility", 1.0) < 0.3:
                continue
            points.append([
                int(float(landmark["x"]) * width),
                int(float(landmark["y"]) * height),
            ])
        if len(points) < 3:
            return
        hull = cv2.convexHull(np.array(points, dtype=np.int32))
        person = np.zeros_like(mask)
        cv2.fillConvexPoly(person, hull, 255)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))
        person = cv2.dilate(person, kernel)
        mask[person > 0] = 255

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
