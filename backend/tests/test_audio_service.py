"""
Unit tests for audio analysis service.

Tests beat detection, closest beat lookup, and rhythm accuracy calculation.
"""

import pytest

from app.services.audio_service import AudioService


@pytest.fixture
def service():
    """Create AudioService instance."""
    return AudioService()


def test_find_closest_beat_exact(service):
    """Test finding exact beat match."""
    beats = [1.0, 2.0, 3.0, 4.0]
    beat, diff = service.find_closest_beat(3.0, beats)

    assert beat == 3.0
    assert diff == 0.0


def test_find_closest_beat_between(service):
    """Test finding closest beat when timestamp is between beats."""
    beats = [1.0, 2.0, 3.0, 4.0]
    beat, diff = service.find_closest_beat(2.4, beats)

    assert beat == 2.0
    assert abs(diff - 0.4) < 0.001


def test_find_closest_beat_empty_list(service):
    """Test closest beat with empty beat list."""
    beat, diff = service.find_closest_beat(5.0, [])

    assert beat == 0.0
    assert diff == 5.0


def test_is_on_beat_true(service):
    """Test timestamp on beat within tolerance."""
    beats = [1.0, 2.0, 3.0]
    assert service.is_on_beat(2.05, beats, tolerance=0.15) is True


def test_is_on_beat_false(service):
    """Test timestamp off beat outside tolerance."""
    beats = [1.0, 2.0, 3.0]
    assert service.is_on_beat(2.5, beats, tolerance=0.15) is False


def test_calculate_rhythm_accuracy_perfect(service):
    """Test rhythm accuracy with all steps on beat."""
    beats = [1.0, 2.0, 3.0, 4.0]
    steps = [1.0, 2.0, 3.0, 4.0]

    result = service.calculate_rhythm_accuracy(steps, beats)

    assert result["accuracy"] == 100.0
    assert result["on_beat"] == 4
    assert result["total"] == 4
    assert len(result["off_beat_steps"]) == 0


def test_calculate_rhythm_accuracy_partial(service):
    """Test rhythm accuracy with some steps off beat."""
    beats = [1.0, 2.0, 3.0, 4.0]
    steps = [1.0, 2.5, 3.0, 4.0]  # 2.5 is off beat

    result = service.calculate_rhythm_accuracy(steps, beats, tolerance=0.15)

    assert result["on_beat"] == 3
    assert result["total"] == 4
    assert result["accuracy"] == 75.0
    assert len(result["off_beat_steps"]) == 1
    assert result["off_beat_steps"][0]["timestamp"] == 2.5


def test_calculate_rhythm_accuracy_empty(service):
    """Test rhythm accuracy with no steps."""
    result = service.calculate_rhythm_accuracy([], [1.0, 2.0])

    assert result["accuracy"] == 0.0
    assert result["total"] == 0
