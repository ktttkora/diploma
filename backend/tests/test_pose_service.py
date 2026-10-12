"""
Unit tests for pose detection service.

Tests step detection and angle calculation using synthetic landmark data.
"""

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


def test_detect_steps_no_movement(service):
    """Test that static poses produce no steps."""
    poses = []
    for i in range(10):
        poses.append({
            "frame": i,
            "timestamp": i * 0.033,
            "landmarks": make_landmarks({27: (0.5, 0.8), 28: (0.6, 0.8)}),
            "detected": True
        })

    steps = service.detect_steps(poses)
    assert len(steps) == 0


def test_detect_steps_with_movement(service):
    """Test that ankle movement produces step detection."""
    poses = []
    for i in range(10):
        # Alternate ankle position to simulate steps
        y_offset = 0.05 if i % 2 == 0 else 0.0
        poses.append({
            "frame": i,
            "timestamp": i * 0.1,
            "landmarks": make_landmarks({
                27: (0.5, 0.8 + y_offset),
                28: (0.6, 0.8)
            }),
            "detected": True
        })

    steps = service.detect_steps(poses)
    assert len(steps) > 0
    assert all(s["foot"] in ("left", "right") for s in steps)


def test_detect_steps_skips_undetected(service):
    """Test that undetected poses are skipped."""
    poses = [
        {"frame": 0, "timestamp": 0.0, "landmarks": [], "detected": False},
        {"frame": 1, "timestamp": 0.1, "landmarks": [], "detected": False},
    ]

    steps = service.detect_steps(poses)
    assert len(steps) == 0
