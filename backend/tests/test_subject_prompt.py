"""
Who the vision model is asked to critique.

The AI transport (_request) is mocked; the Grok CLI is not called.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from app.api.videos import SUBJECT_REQUIRED, normalize_subject
from app.config import settings
from app.services.claude_service import SUBJECT_PROMPTS, ClaudeService


class EmptyReference:
    """Reference stub without catalog or examples."""

    def get_element_catalog(self) -> Dict[str, str]:
        return {}

    def select_example_frames(self, *args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
        return []

    def match_element_name(self, name: str, catalog: Any = None) -> str:
        return name


@pytest.fixture(autouse=True)
def ai_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable AI analysis."""
    monkeypatch.setattr(settings, "AI_ENABLED", True)


def make_frames(tmp_path: Path) -> List[str]:
    path = tmp_path / "user_0.jpg"
    path.write_bytes(b"\xff\xd8\xff\xd9")
    return [str(path)]


def run(service: ClaudeService, frames: List[str], payload: Dict[str, Any],
        subject: str = "both") -> Dict[str, Any]:
    """Run analyze_video with a mocked transport, recording the prompt."""
    captured: Dict[str, Any] = {}

    def fake_request(images: List[str], prompt: str) -> str:
        captured["prompt"] = prompt
        return json.dumps(payload, ensure_ascii=False)

    service._request = fake_request
    result = service.analyze_video(frames, [], tempo=120.0, subject=subject)
    result["_captured"] = captured
    return result


def test_female_prompt_is_woman_only(tmp_path: Path) -> None:
    """A female choice names only the woman, not the man-only instruction."""
    service = ClaudeService(api_key="sk-test", model="m", reference=EmptyReference())
    result = run(service, make_frames(tmp_path), {"errors": []}, subject="female")
    prompt = result["_captured"]["prompt"]

    assert "Разбирай ТОЛЬКО девушку" in prompt
    assert "Ошибки мужчины не включай" in prompt
    assert 'person = "female"' in prompt
    assert "Разбирай ТОЛЬКО мужчину" not in prompt
    assert "одежда, фигура, роль в паре" in prompt
    assert "MediaPipe" in prompt
    assert prompt.count(SUBJECT_PROMPTS["female"]) == 1


def test_female_subject_drops_male_error(tmp_path: Path) -> None:
    """An error tagged male is removed when the subject is the woman."""
    payload = {
        "posture_score": 70,
        "technique_score": 60,
        "musicality_score": 80,
        "errors": [
            {"timestamp": 1.0, "category": "posture", "severity": "high",
             "title": "Её спина", "person": "female"},
            {"timestamp": 2.0, "category": "technique", "severity": "medium",
             "title": "Его шаг", "person": "male"},
        ],
    }
    service = ClaudeService(api_key="sk-test", model="m", reference=EmptyReference())
    result = run(service, make_frames(tmp_path), payload, subject="female")

    assert [err["title"] for err in result["errors"]] == ["Её спина"]
    assert result["errors"][0]["person"] == "female"


def test_female_subject_keeps_missing_person(tmp_path: Path) -> None:
    """A missing person is kept and tagged female when only the woman is chosen."""
    payload = {
        "errors": [
            {"timestamp": 1.0, "category": "posture", "severity": "high",
             "title": "Без метки"},
            {"timestamp": 3.0, "category": "technique", "severity": "low",
             "title": "Чужая метка", "person": "coach"},
            {"timestamp": 4.0, "category": "posture", "severity": "medium",
             "title": "Его руки", "person": "male"},
        ],
    }
    service = ClaudeService(api_key="sk-test", model="m", reference=EmptyReference())
    result = run(service, make_frames(tmp_path), payload, subject="female")

    assert [err["title"] for err in result["errors"]] == ["Без метки", "Чужая метка"]
    assert [err["person"] for err in result["errors"]] == ["female", "female"]


def test_unknown_subject_is_rejected() -> None:
    """Upload validation refuses a subject outside female, male, and both."""
    with pytest.raises(ValueError) as caught:
        normalize_subject("child")
    assert str(caught.value) == SUBJECT_REQUIRED
    assert normalize_subject(" Female ") == "female"
