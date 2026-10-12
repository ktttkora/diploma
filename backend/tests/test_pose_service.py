"""
Unit tests for pose detection service.

Tests step detection and angle calculation using synthetic landmark data.
"""

import math
import pytest
from typing import List, Dict

from app.services.pose_service import PoseService


@pytest.fixture
def service():
    """Create PoseService instance."""
    return PoseService()


def make_landmarks(overrides: Dict[int, tuple] | None = None) -> List[Dict[str, float]]:
    """
    Create synthetic 33-landmark list.

    Args:
        overrides: mapping of landmark_index -> (x, y)

    Returns:
        List of 33 landmark dicts
    """
    landmarks = [
        {"x": 0.5, "y": 0.5, "z": 0.0, "visibility": 1.0}
        for _ in range(33)
    ]
    for idx, value in (overrides or {}).items():
        landmarks[int(idx)] = {
            "x": value[0], "y": value[1], "z": 0.0, "visibility": 1.0
        }
    return landmarks


def test_calculate_angles_straight_legs(service):
    """Test angle calculation with straight vertical legs."""
    # Hip above knee above ankle (all same x = straight leg)
    landmarks = make_landmarks({
        23: (0.5, 0.4),  # left hip
        25: (0.5, 0.6),  # left knee
        27: (0.5, 0.8),  # left ankle
        24: (0.6, 0.4),  # right hip
        26: (0.6, 0.6),  # right knee
        28: (0.6, 0.8),  # right ankle
        11: (0.45, 0.2),  # left shoulder
        12: (0.55, 0.2),  # right shoulder
    })

    angles = service.calculate_angles(landmarks)

    # Straight leg should be ~180 degrees
    assert angles["left_knee_angle"] > 170
    assert angles["right_knee_angle"] > 170


def test_calculate_angles_bent_knee(service):
    """Test angle calculation with bent knee."""
    # Ankle moved forward relative to knee
    landmarks = make_landmarks({
        23: (0.5, 0.4),   # left hip
        25: (0.5, 0.6),   # left knee
        27: (0.35, 0.75),  # left ankle (bent)
        24: (0.6, 0.4),
        26: (0.6, 0.6),
        28: (0.6, 0.8),
        11: (0.45, 0.2),
        12: (0.55, 0.2),
    })

    angles = service.calculate_angles(landmarks)

    # Bent leg should be noticeably less than 180
    assert angles["left_knee_angle"] < 150


def test_calculate_angles_insufficient_landmarks(service):
    """Test that too few landmarks raises error."""
    with pytest.raises(ValueError):
        service.calculate_angles([{"x": 0.5, "y": 0.5, "z": 0.0, "visibility": 1.0}])


def test_calculate_angles_returns_all_keys(service):
    """Test that all expected angle keys are returned."""
    landmarks = make_landmarks()

    angles = service.calculate_angles(landmarks)

    assert "spine_angle" in angles
    assert "left_knee_angle" in angles
    assert "right_knee_angle" in angles



def make_step_cycle(start_time, step_interval, swing_duration, fps=30.0,
                    amplitude=0.12, foot_index=27):
    """
    Build pose frames for repeated foot swings.

    Each cycle lifts the ankle by `amplitude` over `swing_duration` seconds
    and returns it to the start, then waits until the next cycle. Image
    coordinates run downwards, so a lift means y decreasing.

    Args:
        start_time: Timestamp of the first frame in seconds
        step_interval: Time between the start of consecutive steps
        swing_duration: How long one lift-and-return takes
        fps: Frames per second
        amplitude: Swing size in normalised units
        foot_index: Landmark index to move (27 left, 28 right)

    Returns:
        List of pose dicts
    """
    poses = []
    base_y = 0.8
    dt = 1.0 / fps
    total = start_time + step_interval * 8

    t = start_time
    frame = 0
    while t < total:
        phase = (t - start_time) % step_interval
        if phase <= swing_duration:
            progress = phase / swing_duration
            # y decreases on the lift, so subtract
            offset = -amplitude * math.sin(math.pi * progress)
        else:
            offset = 0.0

        poses.append({
            "frame": frame,
            "timestamp": round(t, 4),
            "landmarks": make_landmarks({foot_index: (0.5, base_y + offset)}),
            "detected": True
        })
        frame += 1
        t += dt

    return poses


def test_detect_steps_one_detection_per_step(service):
    """A full lift-and-return cycle yields exactly one step."""
    poses = make_step_cycle(start_time=0.5, step_interval=0.5, swing_duration=0.3)

    steps = service.detect_steps(poses)

    # 8 cycles fit in the generated span
    assert len(steps) == 8


def test_detect_steps_long_swing_not_double_counted(service):
    """A swing longer than min_interval still counts once, not twice."""
    poses = make_step_cycle(start_time=0.5, step_interval=0.6, swing_duration=0.4)

    steps = service.detect_steps(poses)

    assert len(steps) == 8


def test_detect_steps_fast_tempo(service):
    """Steps at 130 BPM (0.46 s apart) are all detected."""
    poses = make_step_cycle(start_time=0.5, step_interval=0.4615, swing_duration=0.25)

    steps = service.detect_steps(poses)

    assert len(steps) == 8


def test_detect_steps_high_frame_rate(service):
    """The same motion at 60 fps gives the same step count."""
    poses = make_step_cycle(start_time=0.5, step_interval=0.5,
                            swing_duration=0.3, fps=60.0)

    steps = service.detect_steps(poses)

    assert len(steps) == 8


def test_detect_steps_no_movement(service):
    """Static poses produce no steps."""
    poses = [
        {"frame": i, "timestamp": i * 0.033,
         "landmarks": make_landmarks({27: (0.5, 0.8), 28: (0.6, 0.8)}),
         "detected": True}
        for i in range(20)
    ]

    assert service.detect_steps(poses) == []


def test_detect_steps_ignores_tiny_movement(service):
    """Jitter below the amplitude threshold is not a step."""
    poses = [
        {"frame": i, "timestamp": i * 0.033,
         "landmarks": make_landmarks({27: (0.5, 0.8 + (0.005 if i % 2 else 0.0))}),
         "detected": True}
        for i in range(20)
    ]

    assert service.detect_steps(poses) == []


def test_detect_steps_skips_undetected(service):
    """Frames without a pose produce nothing."""
    poses = [
        {"frame": 0, "timestamp": 0.0, "landmarks": [], "detected": False},
        {"frame": 1, "timestamp": 0.1, "landmarks": [], "detected": False},
    ]

    assert service.detect_steps(poses) == []


def test_detect_steps_resets_after_gap(service):
    """A long detection gap does not turn into a phantom step."""
    poses = [
        {"frame": 0, "timestamp": 0.0,
         "landmarks": make_landmarks({27: (0.5, 0.80)}), "detected": True},
        # Two seconds later the ankle is somewhere else entirely
        {"frame": 1, "timestamp": 2.0,
         "landmarks": make_landmarks({27: (0.5, 0.95)}), "detected": True},
    ]

    assert service.detect_steps(poses) == []


def test_detect_steps_first_frame_is_not_a_step(service):
    """The very first frame has nothing to compare against."""
    poses = [
        {"frame": 0, "timestamp": 0.0,
         "landmarks": make_landmarks({27: (0.5, 0.9)}), "detected": True},
    ]

    assert service.detect_steps(poses) == []


def test_detect_steps_returns_foot_names(service):
    """Detected steps name the foot that moved."""
    poses = make_step_cycle(start_time=0.5, step_interval=0.5,
                            swing_duration=0.3, foot_index=28)

    steps = service.detect_steps(poses)

    assert steps
    assert all(s["foot"] == "right" for s in steps)
