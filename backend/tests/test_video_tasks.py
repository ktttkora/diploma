"""
Unit tests for key-frame extraction helpers.

Covers timestamp planning and error merging used by the processing
pipeline. Frame extraction itself is exercised end-to-end separately,
since it shells out to ffmpeg.
"""

import pytest

from app.utils.frame_extractor import calculate_key_timestamps
from app.tasks.video_tasks import _merge_errors, _average, MAX_ERRORS


def test_calculate_key_timestamps_count():
    """The requested number of timestamps is produced."""
    timestamps = calculate_key_timestamps(60.0, count=10)
    assert len(timestamps) == 10


def test_calculate_key_timestamps_sorted():
    """Timestamps are returned in ascending order."""
    timestamps = calculate_key_timestamps(60.0, count=10)
    assert timestamps == sorted(timestamps)


def test_calculate_key_timestamps_within_duration():
    """No timestamp falls outside the video."""
    timestamps = calculate_key_timestamps(60.0, count=10)
    assert all(0 < t < 60.0 for t in timestamps)


def test_calculate_key_timestamps_skips_edges():
    """The very start and end of the clip are skipped."""
    timestamps = calculate_key_timestamps(60.0, count=10)
    assert timestamps[0] > 1.0
    assert timestamps[-1] < 59.0


def test_calculate_key_timestamps_rejects_zero_duration():
    """A non-positive duration is rejected."""
    with pytest.raises(ValueError):
        calculate_key_timestamps(0, count=10)


def test_calculate_key_timestamps_rejects_zero_count():
    """A non-positive frame count is rejected."""
    with pytest.raises(ValueError):
        calculate_key_timestamps(60.0, count=0)


def test_merge_errors_combines_both_sources():
    """Rhythm and AI errors both appear in the merged list."""
    rhythm = [{"timestamp": 1.0, "severity": "medium", "title": "Ритм"}]
    ai = [{"timestamp": 2.0, "severity": "high", "title": "Постура"}]

    merged = _merge_errors(rhythm, ai)

    assert len(merged) == 2
    assert {e["title"] for e in merged} == {"Ритм", "Постура"}


def test_merge_errors_sorts_by_severity():
    """More severe errors come first."""
    rhythm = [{"timestamp": 1.0, "severity": "low", "title": "Низкая"}]
    ai = [
        {"timestamp": 5.0, "severity": "critical", "title": "Критичная"},
        {"timestamp": 2.0, "severity": "high", "title": "Высокая"},
    ]

    merged = _merge_errors(rhythm, ai)

    assert [e["title"] for e in merged] == ["Критичная", "Высокая", "Низкая"]


def test_merge_errors_sorts_by_timestamp_within_severity():
    """Errors of equal severity are ordered by time."""
    ai = [
        {"timestamp": 9.0, "severity": "high", "title": "Позже"},
        {"timestamp": 3.0, "severity": "high", "title": "Раньше"},
    ]

    merged = _merge_errors([], ai)

    assert [e["title"] for e in merged] == ["Раньше", "Позже"]


def test_merge_errors_caps_at_max():
    """The list is capped at the maximum number of errors."""
    ai = [
        {"timestamp": float(i), "severity": "high", "title": f"Ошибка {i}"}
        for i in range(25)
    ]

    merged = _merge_errors([], ai)

    assert len(merged) == MAX_ERRORS


def test_merge_errors_defaults_unknown_severity():
    """An unrecognised severity does not break sorting."""
    merged = _merge_errors([], [{"timestamp": 1.0, "severity": "странная"}])
    assert len(merged) == 1


def test_average_ignores_missing_scores():
    """Categories the AI skipped are excluded from the average."""
    assert _average(60.0, None, None, 80.0) == 70.0


def test_average_all_missing():
    """With no scores at all there is no average."""
    assert _average(None, None) is None


def test_average_rounds():
    """The average is rounded to one decimal place."""
    assert _average(62.2) == 62.2
    assert _average(1.0, 2.0, 2.0) == 1.7


def test_merge_errors_drops_near_duplicates():
    """Same-category errors within DUPLICATE_WINDOW collapse to one."""
    rhythm = [
        {"timestamp": 10.855, "severity": "medium"},
        {"timestamp": 10.889, "severity": "medium"},
        {"timestamp": 11.793, "severity": "medium"},
        {"timestamp": 11.793, "severity": "medium"},
    ]
    merged = _merge_errors(rhythm, [])
    assert [e["timestamp"] for e in merged] == [10.855, 11.793]


def test_merge_errors_keeps_more_severe_duplicate():
    """When duplicates differ in severity, the more severe one stays."""
    rhythm = [
        {"timestamp": 5.0, "severity": "medium"},
        {"timestamp": 5.1, "severity": "high"},
    ]
    merged = _merge_errors(rhythm, [])
    assert len(merged) == 1
    assert merged[0]["severity"] == "high"


def test_merge_errors_keeps_different_categories_at_same_time():
    """A rhythm error and an AI error at one moment are both kept."""
    rhythm = [{"timestamp": 3.0, "severity": "medium"}]
    ai = [{"timestamp": 3.0, "category": "posture", "severity": "medium"}]
    merged = _merge_errors(rhythm, ai)
    assert len(merged) == 2
