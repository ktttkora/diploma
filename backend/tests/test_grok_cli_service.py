"""
Unit tests for GrokCliService.

subprocess and shutil.which are mocked, so the real CLI is never run.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

from app.config import settings
from app.services import claude_cli_service as claude_cli_module
from app.services import grok_cli_service as grok_module
from app.services.claude_service import ClaudeUnavailableError, get_ai_service
from app.services.grok_cli_service import GrokCliService, STRIPPED_ENV_VARS

FAKE_CLI = "C:\\fake\\grok.exe"

VALID_ANSWER = {
    "detected_elements": ["Американка"],
    "posture_score": 70,
    "technique_score": 65,
    "musicality_score": 80,
    "errors": [],
}


class EmptyReference:
    """Reference stub without catalog or examples."""

    def get_element_catalog(self) -> Dict[str, str]:
        return {}

    def select_example_frames(self, *args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
        return []

    def match_element_name(self, name: str, catalog: Any = None) -> Optional[str]:
        return name


@pytest.fixture(autouse=True)
def cli_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable AI and make the Grok CLI look installed."""
    monkeypatch.setattr(settings, "AI_ENABLED", True)
    monkeypatch.setattr(claude_cli_module.shutil, "which", lambda name: FAKE_CLI)


def make_frames(tmp_path: Path) -> List[str]:
    """Create one fake JPEG frame."""
    path = tmp_path / "кадр.jpg"
    path.write_bytes(b"\xff\xd8fake")
    return [str(path)]


class FakeProcess:
    """Stand-in for a running CLI process."""

    pid = 4242

    def __init__(self, owner: "FakeRun"):
        self.owner = owner
        self.returncode = owner.returncode

    def communicate(self, input: Optional[str] = None,
                    timeout: Optional[float] = None) -> Tuple[str, str]:
        self.owner.calls[-1].update({"input": input, "timeout": timeout})
        if self.owner.exc is not None:
            raise self.owner.exc
        return self.owner.stdout, self.owner.stderr


class FakeRun:
    """Replaces subprocess.Popen and records the call."""

    def __init__(self, stdout: str, returncode: int = 0, stderr: str = ""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr
        self.exc = None
        self.calls: List[Dict[str, Any]] = []

    def __call__(self, command: List[str], **kwargs: Any) -> FakeProcess:
        self.calls.append({"command": command, **kwargs})
        return FakeProcess(self)


def make_service() -> GrokCliService:
    """Service with an empty reference."""
    return GrokCliService(cli_path="grok", model="", timeout=30, reference=EmptyReference())


def grok_output(text: str) -> str:
    """Build stdout of `grok --output-format json`."""
    return json.dumps({
        "text": text,
        "stopReason": "end_turn",
        "num_turns": 2,
    }, ensure_ascii=False)


def test_success_parses_text_field(tmp_path, monkeypatch) -> None:
    """The subscription CLI answer is taken from the text field."""
    fake = FakeRun(stdout=grok_output(json.dumps(VALID_ANSWER, ensure_ascii=False)))
    monkeypatch.setattr(grok_module.subprocess, "Popen", fake)

    result = make_service().analyze_video(make_frames(tmp_path), [], tempo=120)

    assert result["posture_score"] == 70
    command = fake.calls[0]["command"]
    assert command[0] == FAKE_CLI
    assert "--prompt-file" in command
    assert "XAI_API_KEY" not in command
    env = fake.calls[0]["env"]
    for name in STRIPPED_ENV_VARS:
        assert name not in env


def test_api_key_in_parent_env_is_not_passed(tmp_path, monkeypatch) -> None:
    """A key in the parent process must not switch Grok off the subscription."""
    monkeypatch.setenv("XAI_API_KEY", "secret-key")
    monkeypatch.setenv("XAI_API_BASE_URL", "http://203.0.113.5")
    fake = FakeRun(stdout=grok_output(json.dumps(VALID_ANSWER)))
    monkeypatch.setattr(grok_module.subprocess, "Popen", fake)

    make_service().analyze_video(make_frames(tmp_path), [], tempo=120)

    env = fake.calls[0]["env"]
    assert "XAI_API_KEY" not in env
    assert "XAI_API_BASE_URL" not in env


def test_not_signed_in_message(tmp_path, monkeypatch) -> None:
    """A login failure tells the user to run grok login."""
    fake = FakeRun(stdout="", returncode=1, stderr="Not logged in · Please run grok login")
    monkeypatch.setattr(grok_module.subprocess, "Popen", fake)

    with pytest.raises(ClaudeUnavailableError, match="grok login"):
        make_service().analyze_video(make_frames(tmp_path), [], tempo=120)


def test_get_ai_service_selects_grok(monkeypatch) -> None:
    """AI_PROVIDER=grok_cli selects GrokCliService."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "grok_cli")
    monkeypatch.setattr(grok_module, "_grok_cli_service", None)

    assert isinstance(get_ai_service(), GrokCliService)
