"""
Tests for frame timestamps in the AI prompt and timestamp clamping.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from app.config import settings
from app.services.claude_service import ClaudeService
from app.utils.frame_extractor import parse_frame_timestamp

ANSWER = {
    "detected_elements": [],
    "posture_score": 70,
    "technique_score": 70,
    "musicality_score": 70,
    "errors": [
        {"timestamp": 3, "category": "posture", "severity": "high", "title": "A"},
        {"timestamp": 500.0, "category": "posture", "severity": "low", "title": "B"},
        {"timestamp": -2, "category": "posture", "severity": "low", "title": "C"},
    ],
}


class EmptyReference:
    """Reference stub without catalog or examples."""

    def get_element_catalog(self) -> Dict[str, str]:
        return {}

    def select_example_frames(self, *args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
        return []

    def match_element_name(self, name: str, catalog: Any = None) -> Optional[str]:
        return name


class CapturingService(ClaudeService):
    """ClaudeService that records the prompt instead of calling the API."""

    def __init__(self) -> None:
        super().__init__(api_key="test-key", model="test", reference=EmptyReference())
        self.prompt = ""

    def _request(self, frames: List[str], prompt: str) -> str:
        self.prompt = prompt
        return json.dumps(ANSWER)


@pytest.fixture(autouse=True)
def ai_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable AI analysis."""
    monkeypatch.setattr(settings, "AI_ENABLED", True)


def make_key_frames(tmp_path: Path, timestamps: List[float]) -> List[str]:
    """Create frames named like extract_key_frames output."""
    paths = []
    for i, ts in enumerate(timestamps):
        path = tmp_path / f"key_{i:04d}_{ts:.2f}s.jpg"
        path.write_bytes(b"\xff\xd8fake")
        paths.append(str(path))
    return paths


@pytest.mark.parametrize("name, expected", [
    ("key_0000_8.56s.jpg", 8.56),
    ("key_0012_120.00s.JPG", 120.0),
    ("C:/кадры/key_0001_21s.png", 21.0),
    ("frame.jpg", None),
    ("key_0001_abc.jpg", None),
])
def test_parse_frame_timestamp(name: str, expected: Optional[float]) -> None:
    """Timestamps are read from key frame names, others give None."""
    assert parse_frame_timestamp(name) == expected


def test_prompt_labels_frames_with_time_from_names(tmp_path) -> None:
    """Each user image is labelled with its video time in seconds."""
    service = CapturingService()
    frames = make_key_frames(tmp_path, [8.56, 21.41, 34.25])

    service.analyze_video(frames, [])

    assert "- Изображение 1 (t=8.56 с)" in service.prompt
    assert "- Изображение 2 (t=21.41 с)" in service.prompt
    assert "- Изображение 3 (t=34.25 с)" in service.prompt
    assert "СЕКУНДАХ от начала видео" in service.prompt


def test_explicit_timestamps_override_names(tmp_path) -> None:
    """Passed frame_timestamps win over file names; missing ones stay unlabelled."""
    service = CapturingService()
    frames = make_key_frames(tmp_path, [1.0, 2.0])

    service.analyze_video(frames, [], frame_timestamps=[5.5])

    assert "- Изображение 1 (t=5.50 с)" in service.prompt
    assert "- Изображение 2\n" in service.prompt


def test_no_timestamps_no_frames_section(tmp_path) -> None:
    """Frames without timestamps do not add the section."""
    service = CapturingService()
    path = tmp_path / "frame.jpg"
    path.write_bytes(b"\xff\xd8fake")

    service.analyze_video([str(path)], [])

    assert "КАДРЫ ВИДЕО" not in service.prompt


def test_timestamps_clamped_to_duration(tmp_path) -> None:
    """Error timestamps are clamped to [0, duration]."""
    service = CapturingService()
    frames = make_key_frames(tmp_path, [8.56])

    result = service.analyze_video(frames, [], duration=40.0)

    assert [e["timestamp"] for e in result["errors"]] == [3.0, 40.0, 0.0]


def test_timestamps_without_duration_only_floor(tmp_path) -> None:
    """Without duration only negative timestamps are fixed."""
    service = CapturingService()
    frames = make_key_frames(tmp_path, [8.56])

    result = service.analyze_video(frames, [])

    assert [e["timestamp"] for e in result["errors"]] == [3.0, 500.0, 0.0]
