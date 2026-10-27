"""
Unit tests for ClaudeCliService (local Claude Code CLI provider).

subprocess and shutil.which are mocked, so the real CLI is never run.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

from app.config import settings
from app.services import claude_cli_service as cli_module
from app.services.claude_cli_service import ClaudeCliService
from app.services.claude_service import ClaudeUnavailableError, get_ai_service

FAKE_CLI = "C:\\fake\\claude.exe"

VALID_ANSWER = {
    "detected_elements": ["Американка"],
    "posture_score": 70,
    "technique_score": 65,
    "musicality_score": 80,
    "errors": [{
        "timestamp": 1.5,
        "category": "posture",
        "severity": "high",
        "title": "Сутулая спина",
        "description": "Плечи опущены",
        "recommendation": "Выпрямитесь",
        "detected_element": None,
    }],
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
    """Enable AI and make the CLI look installed."""
    monkeypatch.setattr(settings, "AI_ENABLED", True)
    monkeypatch.setattr(cli_module.shutil, "which", lambda name: FAKE_CLI)


def make_frames(tmp_path: Path, count: int) -> List[str]:
    """Create fake JPEG frames in a folder with a Cyrillic name."""
    folder = tmp_path / "кадры"
    folder.mkdir()
    paths = []
    for i in range(count):
        path = folder / f"кадр_{i}.jpg"
        path.write_bytes(b"\xff\xd8fake" + bytes([i]))
        paths.append(str(path))
    return paths


def cli_output(result: str, is_error: bool = False) -> str:
    """Build stdout of `claude -p --output-format json`."""
    return json.dumps({
        "type": "result",
        "subtype": "error_during_execution" if is_error else "success",
        "is_error": is_error,
        "result": result,
    }, ensure_ascii=False)


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
    """Replaces subprocess.Popen: records the call, returns a canned result."""

    def __init__(self, stdout: str = "", returncode: int = 0,
                 stderr: str = "", exc: Optional[BaseException] = None):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr
        self.exc = exc
        self.calls: List[Dict[str, Any]] = []
        self.staged: List[bytes] = []

    def __call__(self, command: List[str], **kwargs: Any) -> FakeProcess:
        self.calls.append({"command": command, **kwargs})
        cwd = Path(kwargs["cwd"])
        self.staged = [p.read_bytes() for p in sorted(cwd.iterdir())]
        return FakeProcess(self)


@pytest.fixture
def killed(monkeypatch: pytest.MonkeyPatch) -> List[int]:
    """Record process-tree kills instead of running taskkill."""
    pids: List[int] = []
    monkeypatch.setattr(ClaudeCliService, "_kill_tree",
                        staticmethod(lambda process: pids.append(process.pid)))
    return pids


def make_service() -> ClaudeCliService:
    """Service with an empty reference and default CLI settings."""
    return ClaudeCliService(cli_path="claude", model="", timeout=30,
                            reference=EmptyReference())


def test_success_returns_normalized_result(tmp_path, monkeypatch) -> None:
    """A clean JSON answer is parsed and normalized."""
    frames = make_frames(tmp_path, 3)
    fake = FakeRun(stdout=cli_output(json.dumps(VALID_ANSWER, ensure_ascii=False)))
    monkeypatch.setattr(cli_module.subprocess, "Popen", fake)

    result = make_service().analyze_video(frames, [], tempo=120)

    assert result["posture_score"] == 70
    assert result["detected_elements"] == ["Американка"]
    assert result["errors"][0]["title"] == "Сутулая спина"


def test_command_is_isolated_and_read_only(tmp_path, monkeypatch) -> None:
    """Only Read is allowed, user settings are skipped, no shell is used."""
    frames = make_frames(tmp_path, 2)
    fake = FakeRun(stdout=cli_output(json.dumps(VALID_ANSWER)))
    monkeypatch.setattr(cli_module.subprocess, "Popen", fake)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret")
    monkeypatch.setenv("CLAUDECODE", "1")

    make_service().analyze_video(frames, [])

    call = fake.calls[0]
    command = call["command"]
    assert command[0] == FAKE_CLI
    assert "-p" in command
    assert command[command.index("--output-format") + 1] == "json"
    assert command[command.index("--tools") + 1] == "Read"
    assert command[command.index("--allowedTools") + 1] == "Read(./**)"
    assert command[command.index("--permission-mode") + 1] == "dontAsk"
    assert "--restricted" in command
    assert "--safe-mode" in command
    assert "--model" not in command
    for forbidden in ("Bash", "Write", "Edit", "WebFetch"):
        assert not any(forbidden in arg for arg in command[:-1])
    assert call["shell"] is False
    assert call["encoding"] == "utf-8"
    assert call["timeout"] == 30
    if os.name == "nt":
        assert call["creationflags"] & subprocess.CREATE_NEW_PROCESS_GROUP
    assert "ANTHROPIC_API_KEY" not in call["env"]
    assert "CLAUDECODE" not in call["env"]
    assert Path(call["cwd"]).resolve() != Path.cwd().resolve()


def test_frames_are_staged_in_prompt_order(tmp_path, monkeypatch) -> None:
    """Frames are copied under ASCII names and listed in the same order."""
    frames = make_frames(tmp_path, 3)
    fake = FakeRun(stdout=cli_output(json.dumps(VALID_ANSWER)))
    monkeypatch.setattr(cli_module.subprocess, "Popen", fake)

    make_service().analyze_video(frames, [])

    prompt = fake.calls[0]["input"]
    assert fake.staged == [Path(p).read_bytes() for p in frames]
    for i in range(1, 4):
        line = next(l for l in prompt.splitlines() if l.startswith(f"Изображение {i}:"))
        assert line.endswith(f"image_{i:02d}.jpg")
        assert Path(line.split(": ", 1)[1]).is_absolute()
    assert "кадр_" not in prompt


def test_model_flag_is_passed_when_configured(tmp_path, monkeypatch) -> None:
    """A configured model is passed with --model."""
    frames = make_frames(tmp_path, 1)
    fake = FakeRun(stdout=cli_output(json.dumps(VALID_ANSWER)))
    monkeypatch.setattr(cli_module.subprocess, "Popen", fake)
    service = ClaudeCliService(cli_path="claude", model="sonnet", timeout=30,
                               reference=EmptyReference())

    service.analyze_video(frames, [])

    command = fake.calls[0]["command"]
    assert command[command.index("--model") + 1] == "sonnet"


def test_fenced_answer_is_parsed(tmp_path, monkeypatch) -> None:
    """An answer wrapped in ```json fences is still parsed."""
    frames = make_frames(tmp_path, 1)
    fenced = "```json\n" + json.dumps(VALID_ANSWER, ensure_ascii=False) + "\n```"
    monkeypatch.setattr(cli_module.subprocess, "Popen", FakeRun(stdout=cli_output(fenced)))

    result = make_service().analyze_video(frames, [])

    assert result["technique_score"] == 65


def test_answer_with_prose_is_parsed(tmp_path, monkeypatch) -> None:
    """Prose around the JSON object is cut off."""
    frames = make_frames(tmp_path, 1)
    text = "Вот анализ:\n" + json.dumps(VALID_ANSWER) + "\nГотово."
    monkeypatch.setattr(cli_module.subprocess, "Popen", FakeRun(stdout=cli_output(text)))

    result = make_service().analyze_video(frames, [])

    assert result["musicality_score"] == 80


def test_is_error_raises_unavailable(tmp_path, monkeypatch) -> None:
    """is_error in the CLI result raises ClaudeUnavailableError."""
    frames = make_frames(tmp_path, 1)
    fake = FakeRun(stdout=cli_output("API Error: 500", is_error=True), returncode=1)
    monkeypatch.setattr(cli_module.subprocess, "Popen", fake)

    with pytest.raises(ClaudeUnavailableError, match="Claude CLI failed"):
        make_service().analyze_video(frames, [])


def test_subscription_limit_raises_unavailable(tmp_path, monkeypatch) -> None:
    """A usage limit message is reported as a subscription limit."""
    frames = make_frames(tmp_path, 1)
    fake = FakeRun(stdout=cli_output("Claude AI usage limit reached|1700000000",
                                     is_error=True))
    monkeypatch.setattr(cli_module.subprocess, "Popen", fake)

    with pytest.raises(ClaudeUnavailableError, match="subscription limit"):
        make_service().analyze_video(frames, [])


def test_nonzero_exit_without_json_raises(tmp_path, monkeypatch) -> None:
    """A crash without JSON output raises ClaudeUnavailableError."""
    frames = make_frames(tmp_path, 1)
    fake = FakeRun(stdout="", stderr="boom", returncode=2)
    monkeypatch.setattr(cli_module.subprocess, "Popen", fake)

    with pytest.raises(ClaudeUnavailableError, match="exit code 2"):
        make_service().analyze_video(frames, [])


def test_timeout_kills_tree_and_raises(tmp_path, monkeypatch, killed) -> None:
    """A timeout kills the process tree and raises ClaudeUnavailableError."""
    frames = make_frames(tmp_path, 1)
    fake = FakeRun(exc=subprocess.TimeoutExpired(cmd="claude", timeout=30))
    monkeypatch.setattr(cli_module.subprocess, "Popen", fake)

    with pytest.raises(ClaudeUnavailableError, match="timed out"):
        make_service().analyze_video(frames, [])
    assert killed == [FakeProcess.pid]


def test_soft_time_limit_kills_tree_and_propagates(tmp_path, monkeypatch, killed) -> None:
    """Celery SoftTimeLimitExceeded kills the process tree and is re-raised."""
    from celery.exceptions import SoftTimeLimitExceeded

    frames = make_frames(tmp_path, 1)
    monkeypatch.setattr(cli_module.subprocess, "Popen",
                        FakeRun(exc=SoftTimeLimitExceeded()))

    with pytest.raises(SoftTimeLimitExceeded):
        make_service().analyze_video(frames, [])
    assert killed == [FakeProcess.pid]


def test_error_messages_do_not_leak_cli_output(tmp_path, monkeypatch) -> None:
    """Raw CLI output stays out of the exception message."""
    frames = make_frames(tmp_path, 1)
    fake = FakeRun(stdout=cli_output("SECRET=abc leaked", is_error=True),
                   stderr="SECRET stderr", returncode=1)
    monkeypatch.setattr(cli_module.subprocess, "Popen", fake)

    with pytest.raises(ClaudeUnavailableError) as info:
        make_service().analyze_video(frames, [])
    assert "SECRET" not in str(info.value)


@pytest.mark.skipif(os.name != "nt", reason="taskkill is Windows-only")
def test_kill_tree_uses_taskkill(monkeypatch) -> None:
    """On Windows the whole process tree is killed with taskkill /T /F."""
    commands: List[List[str]] = []
    monkeypatch.setattr(cli_module.subprocess, "run",
                        lambda command, **kwargs: commands.append(command))

    class Proc:
        pid = 77

        def kill(self) -> None:
            pass

        def communicate(self, timeout: Optional[float] = None) -> Tuple[str, str]:
            return "", ""

    ClaudeCliService._kill_tree(Proc())

    assert commands == [["taskkill", "/T", "/F", "/PID", "77"]]


def test_cli_not_found(tmp_path, monkeypatch) -> None:
    """Without the CLI the service is not configured and refuses to run."""
    monkeypatch.setattr(cli_module.shutil, "which", lambda name: None)
    service = make_service()

    assert service.is_configured is False
    with pytest.raises(ClaudeUnavailableError):
        service.analyze_video(make_frames(tmp_path, 1), [])
    with pytest.raises(ClaudeUnavailableError, match="not found"):
        service._request(["x.jpg"], "prompt")


def test_is_configured_respects_ai_enabled(monkeypatch) -> None:
    """AI_ENABLED=False disables the provider even with the CLI present."""
    service = make_service()
    assert service.is_configured is True
    monkeypatch.setattr(settings, "AI_ENABLED", False)
    assert service.is_configured is False


def test_get_ai_service_selects_cli(monkeypatch) -> None:
    """AI_PROVIDER=claude_cli selects ClaudeCliService."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "claude_cli")
    monkeypatch.setattr(cli_module, "_claude_cli_service", None)

    assert isinstance(get_ai_service(), ClaudeCliService)
