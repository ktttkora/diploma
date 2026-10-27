"""
Unit tests for passing reference elements and examples to the AI.

The AI transport (_request) is mocked; no real API calls are made.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from app.config import settings
from app.services.claude_service import ClaudeService, DEFAULT_ELEMENTS_TASK
from app.services.glm_service import GLMService


AI_RESPONSE = {
    "detected_elements": ["американка", "Йо-йо", "Партнерша Свитч"],
    "posture_score": 70,
    "technique_score": 65,
    "musicality_score": 80,
    "errors": [
        {"timestamp": 3.0, "category": "posture", "severity": "high",
         "title": "Спина", "description": "", "recommendation": "",
         "detected_element": "Партнерша Свитчь"},
        {"timestamp": 5.0, "category": "technique", "severity": "medium",
         "title": "Шаг", "description": "", "recommendation": "",
         "detected_element": "Неизвестный элемент"},
    ],
}


class FakeReference:
    """Stand-in for ReferenceService with a fixed catalog and examples."""

    def __init__(self, catalog: Dict[str, str], examples: List[Dict[str, Any]],
                 fail_examples: bool = False, fail_catalog: bool = False):
        self.catalog = catalog
        self.examples = examples
        self.fail_examples = fail_examples
        self.fail_catalog = fail_catalog
        self.example_calls: List[Dict[str, Any]] = []

    def get_element_catalog(self) -> Dict[str, str]:
        if self.fail_catalog:
            raise OSError("disk error")
        return dict(self.catalog)

    def select_example_frames(self, user_poses, max_images, **kwargs):
        self.example_calls.append({"max_images": max_images, **kwargs})
        if self.fail_examples:
            raise RuntimeError("index broken")
        return self.examples

    def match_element_name(self, name, catalog=None):
        from app.services.reference_service import ReferenceService
        return ReferenceService.match_element_name(self, name, catalog)


@pytest.fixture(autouse=True)
def ai_settings(monkeypatch):
    """Enable AI and reference examples with known limits."""
    monkeypatch.setattr(settings, "AI_ENABLED", True)
    monkeypatch.setattr(settings, "AI_REFERENCE_EXAMPLES", True)
    monkeypatch.setattr(settings, "AI_MAX_IMAGES", 24)
    monkeypatch.setattr(settings, "AI_REFERENCE_CANDIDATES", 8)
    monkeypatch.setattr(settings, "AI_REFERENCE_FRAMES_PER_ELEMENT", 2)


def make_frames(tmp_path: Path, count: int, prefix: str = "user") -> List[str]:
    paths = []
    for i in range(count):
        p = tmp_path / f"{prefix}_{i}.jpg"
        p.write_bytes(b"\xff\xd8\xff\xd9")
        paths.append(str(p))
    return paths


def run(service: ClaudeService, frames: List[str],
        user_poses: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """Run analyze_video with a mocked transport, recording the request."""
    captured: Dict[str, Any] = {}

    def fake_request(images: List[str], prompt: str) -> str:
        captured["images"] = images
        captured["prompt"] = prompt
        return "```json\n" + json.dumps(AI_RESPONSE, ensure_ascii=False) + "\n```"

    service._request = fake_request
    result = service.analyze_video(frames, [], tempo=120.0, user_poses=user_poses)
    result["_captured"] = captured
    return result


CATALOG = {"Американка": "Американка", "Партнерша Свитч": "!_Партнерша_Свитч",
           "Солнышко": "Солнышко"}


@pytest.mark.parametrize("service_cls", [ClaudeService, GLMService])
def test_prompt_lists_elements_and_examples(tmp_path, service_cls) -> None:
    """Both providers get the element list and example images after user frames."""
    examples = [
        {"element": "Американка", "stem": "Американка", "score": 0.1,
         "frame_paths": make_frames(tmp_path, 2, "ref_a")},
        {"element": "Солнышко", "stem": "Солнышко", "score": 0.2,
         "frame_paths": make_frames(tmp_path, 1, "ref_b")},
    ]
    reference = FakeReference(CATALOG, examples)
    service = service_cls(api_key="sk-test", model="test-model", reference=reference)
    user = make_frames(tmp_path, 20)

    result = run(service, user, user_poses=[{"landmarks": []}])
    captured = result["_captured"]

    assert captured["images"] == user + examples[0]["frame_paths"] + examples[1]["frame_paths"]
    prompt = captured["prompt"]
    assert "Американка; Партнерша Свитч; Солнышко" in prompt
    assert "1-20" in prompt
    assert "изображения 21-22: Американка" in prompt
    assert "изображения 23: Солнышко" in prompt
    # Budget = total image limit minus user frames
    assert reference.example_calls[0]["max_images"] == 4


def test_element_names_are_matched_to_catalog(tmp_path) -> None:
    """AI names map onto the catalog: case, fuzzy, or None when unknown."""
    service = ClaudeService(api_key="sk-test", model="m",
                            reference=FakeReference(CATALOG, []))
    result = run(service, make_frames(tmp_path, 5))

    assert result["detected_elements"] == ["Американка", "Партнерша Свитч"]
    assert result["errors"][0]["detected_element"] == "Партнерша Свитч"
    assert result["errors"][1]["detected_element"] is None


def test_no_references_keeps_old_behaviour(tmp_path) -> None:
    """Without references the prompt and names are as before."""
    reference = FakeReference({}, [])
    service = ClaudeService(api_key="sk-test", model="m", reference=reference)
    user = make_frames(tmp_path, 5)

    result = run(service, user, user_poses=[{"landmarks": []}])

    assert result["_captured"]["images"] == user
    assert DEFAULT_ELEMENTS_TASK in result["_captured"]["prompt"]
    assert reference.example_calls == []
    assert result["errors"][1]["detected_element"] == "Неизвестный элемент"


def test_example_failure_degrades_gracefully(tmp_path, caplog) -> None:
    """A failing example selection logs a warning; analysis still runs."""
    reference = FakeReference(CATALOG, [], fail_examples=True)
    service = ClaudeService(api_key="sk-test", model="m", reference=reference)
    user = make_frames(tmp_path, 5)

    with caplog.at_level("WARNING"):
        result = run(service, user, user_poses=[{"landmarks": []}])

    assert result["_captured"]["images"] == user
    assert "Американка; Партнерша Свитч" in result["_captured"]["prompt"]
    assert "Reference example selection failed" in caplog.text


def test_catalog_failure_degrades_gracefully(tmp_path, caplog) -> None:
    """A failing catalog falls back to the original prompt."""
    reference = FakeReference(CATALOG, [], fail_catalog=True)
    service = ClaudeService(api_key="sk-test", model="m", reference=reference)

    with caplog.at_level("WARNING"):
        result = run(service, make_frames(tmp_path, 5), user_poses=[{"landmarks": []}])

    assert DEFAULT_ELEMENTS_TASK in result["_captured"]["prompt"]
    assert result["posture_score"] == 70.0
    assert "Reference element list unavailable" in caplog.text


def test_examples_disabled_or_no_poses(tmp_path, monkeypatch) -> None:
    """Examples are skipped when disabled or when user poses are missing."""
    reference = FakeReference(CATALOG, [{"element": "Американка",
                                         "frame_paths": make_frames(tmp_path, 1, "r")}])
    service = ClaudeService(api_key="sk-test", model="m", reference=reference)
    user = make_frames(tmp_path, 5)

    assert run(service, user, user_poses=None)["_captured"]["images"] == user

    monkeypatch.setattr(settings, "AI_REFERENCE_EXAMPLES", False)
    assert run(service, user, user_poses=[{"landmarks": []}])["_captured"]["images"] == user
    assert reference.example_calls == []


def test_missing_example_frames_are_dropped(tmp_path, caplog) -> None:
    """Example paths that vanished are filtered before encoding."""
    present = make_frames(tmp_path, 1, "ref_ok")
    examples = [
        {"element": "Американка", "frame_paths": present + [str(tmp_path / "gone.jpg")]},
        {"element": "Солнышко", "frame_paths": [str(tmp_path / "gone2.jpg")]},
    ]
    service = ClaudeService(api_key="sk-test", model="m",
                            reference=FakeReference(CATALOG, examples))
    user = make_frames(tmp_path, 1)

    with caplog.at_level("WARNING"):
        result = run(service, user, user_poses=[{"landmarks": []}])

    captured = result["_captured"]
    assert captured["images"] == user + present
    assert "ИЗОБРАЖЕНИЯ: 1 - кадры" in captured["prompt"]
    assert "изображения 2: Американка" in captured["prompt"]
    assert "Солнышко" not in captured["prompt"].split("ЭЛЕМЕНТЫ")[0]
    assert "Dropped unreadable example frames" in caplog.text


def test_soft_time_limit_propagates(tmp_path) -> None:
    """Celery's soft time limit is not swallowed by graceful degradation."""
    from celery.exceptions import SoftTimeLimitExceeded

    class TimeoutReference(FakeReference):
        def select_example_frames(self, *args, **kwargs):
            raise SoftTimeLimitExceeded()

    service = ClaudeService(api_key="sk-test", model="m",
                            reference=TimeoutReference(CATALOG, []))
    with pytest.raises(SoftTimeLimitExceeded):
        run(service, make_frames(tmp_path, 2), user_poses=[{"landmarks": []}])


def test_user_aspect_is_passed_to_reference(tmp_path) -> None:
    """The user video aspect ratio reaches example selection."""
    reference = FakeReference(CATALOG, [])
    service = ClaudeService(api_key="sk-test", model="m", reference=reference)
    service._request = lambda images, prompt: json.dumps(AI_RESPONSE, ensure_ascii=False)
    service.analyze_video(make_frames(tmp_path, 2), [], user_poses=[{"landmarks": []}],
                          user_aspect=0.5625)
    assert reference.example_calls[0]["user_aspect"] == 0.5625


def test_user_frames_fill_budget(tmp_path, monkeypatch) -> None:
    """When user frames use the whole image limit, no examples are requested."""
    monkeypatch.setattr(settings, "AI_MAX_IMAGES", 10)
    reference = FakeReference(CATALOG, [])
    service = ClaudeService(api_key="sk-test", model="m", reference=reference)

    result = run(service, make_frames(tmp_path, 20), user_poses=[{"landmarks": []}])

    assert len(result["_captured"]["images"]) == 10
    assert reference.example_calls == []
