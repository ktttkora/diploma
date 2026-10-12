"""
Unit tests for reference service.

Tests loading reference poses from JSON files.
"""

import pytest
import json
import tempfile
from pathlib import Path

from app.services.reference_service import ReferenceService


@pytest.fixture
def temp_reference_dir():
    """Create temporary directory with test reference JSON files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test reference file
        ref_data = {
            "element": "TestElement",
            "total_frames": 100,
            "fps": 30.0,
            "poses_count": 3,
            "poses": [
                {"frame": 0, "timestamp": 0.0, "landmarks": [{"x": 0.5, "y": 0.5, "z": 0.0, "visibility": 1.0}] * 33},
                {"frame": 50, "timestamp": 1.667, "landmarks": [{"x": 0.6, "y": 0.6, "z": 0.0, "visibility": 1.0}] * 33},
                {"frame": 99, "timestamp": 3.3, "landmarks": [{"x": 0.7, "y": 0.7, "z": 0.0, "visibility": 1.0}] * 33},
            ]
        }

        with open(Path(tmpdir) / "TestElement.json", "w", encoding="utf-8") as f:
            json.dump(ref_data, f)

        yield tmpdir


def test_list_available_elements(temp_reference_dir):
    """Test listing available reference elements."""
    service = ReferenceService(temp_reference_dir)
    elements = service.list_available_elements()

    assert "TestElement" in elements


def test_get_reference(temp_reference_dir):
    """Test loading reference data."""
    service = ReferenceService(temp_reference_dir)
    ref = service.get_reference("TestElement")

    assert ref is not None
    assert ref["element"] == "TestElement"
    assert ref["poses_count"] == 3
    assert len(ref["poses"]) == 3


def test_get_reference_not_found(temp_reference_dir):
    """Test loading non-existent reference returns None."""
    service = ReferenceService(temp_reference_dir)
    ref = service.get_reference("NonExistent")

    assert ref is None


def test_get_reference_caching(temp_reference_dir):
    """Test that reference is cached after first load."""
    service = ReferenceService(temp_reference_dir)

    ref1 = service.get_reference("TestElement")
    ref2 = service.get_reference("TestElement")

    assert ref1 is ref2  # Same object from cache


def test_find_similar_pose(temp_reference_dir):
    """Test finding closest reference pose by timestamp."""
    service = ReferenceService(temp_reference_dir)

    pose = service.find_similar_pose("TestElement", 1.5)

    assert pose is not None
    assert pose["timestamp"] == 1.667  # Closest to 1.5


def test_find_similar_pose_nonexistent_element(temp_reference_dir):
    """Test finding pose for non-existent element returns None."""
    service = ReferenceService(temp_reference_dir)
    pose = service.find_similar_pose("NonExistent", 1.0)

    assert pose is None


def test_get_reference_frame_at_ratio(temp_reference_dir):
    """Test getting reference pose by relative position."""
    service = ReferenceService(temp_reference_dir)

    start = service.get_reference_frame_at_ratio("TestElement", 0.0)
    middle = service.get_reference_frame_at_ratio("TestElement", 0.5)
    end = service.get_reference_frame_at_ratio("TestElement", 1.0)

    assert start["timestamp"] == 0.0
    assert end["timestamp"] == 3.3
    assert middle is not None


def test_clear_cache(temp_reference_dir):
    """Test clearing the cache."""
    service = ReferenceService(temp_reference_dir)
    service.get_reference("TestElement")

    service.clear_cache()

    assert len(service._cache) == 0


def test_get_stats(temp_reference_dir):
    """Test getting service statistics."""
    service = ReferenceService(temp_reference_dir)
    stats = service.get_stats()

    assert stats["total_elements"] == 1
    assert stats["total_poses"] == 3
    assert "TestElement" in stats["elements"]


def test_missing_directory():
    """Test service handles missing directory gracefully."""
    service = ReferenceService("nonexistent/path")

    assert service.list_available_elements() == []
    assert service.get_reference("anything") is None
