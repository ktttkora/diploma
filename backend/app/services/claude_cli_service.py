"""
Claude Code CLI service for posture/technique/musicality analysis.

Temporary provider for users who have a claude.ai subscription but no
Anthropic API key: runs the local Claude Code CLI in headless mode
(`claude -p`) and lets it look at the frames with its Read tool.

Reuses the prompt, response parsing and normalization of ClaudeService
and only swaps the transport.
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.services.claude_service import ClaudeService, ClaudeUnavailableError
from app.services.reference_service import ReferenceService

logger = logging.getLogger(__name__)

# Replaces the default coding-agent system prompt of Claude Code
CLI_SYSTEM_PROMPT = (
    "You are a dance technique analysis engine. The user message lists image "
    "files by number. Use the Read tool to view every listed image, in order, "
    "before answering. Do not use any other tool and do not ask questions. "
    "Your final answer must be ONLY the JSON object requested by the user "
    "message: no markdown, no code fences, no comments, no text before or "
    "after the JSON."
)

# Environment variables that must not leak into the CLI child process:
# API credentials would switch it off the subscription, and the session
# variables of a parent Claude Code would make it act as a nested session
STRIPPED_ENV_VARS = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "CLAUDECODE",
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_CODE_SESSION_ID",
    "CLAUDE_CODE_CHILD_SESSION",
    "CLAUDE_CODE_SESSION_ATTENDED",
    "CLAUDE_CODE_MESSAGING_SOCKET",
    "CLAUDE_CODE_MESSAGING_TOKEN",
    "CLAUDE_CODE_EXECPATH",
    "CLAUDE_PID",
    "CLAUDE_EFFORT",
)

# Permission rule: Read is allowed only for files under the CLI cwd
READ_RULE = "Read(./**)"

# Seconds to wait for a killed CLI process to release its pipes
KILL_WAIT_SECONDS = 5

# Substrings of CLI error messages that mean the subscription quota is spent
LIMIT_MARKERS = ("usage limit", "rate limit", "limit reached", "quota")


class ClaudeCliService(ClaudeService):
    """Service for dance analysis through the local Claude Code CLI."""

    def __init__(
        self,
        cli_path: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        reference: Optional[ReferenceService] = None
    ):
        """
        Initialize Claude CLI service.

        Args:
            cli_path: CLI executable name or path (defaults to settings.CLAUDE_CLI_PATH)
            model: Model alias or ID (defaults to settings.CLAUDE_CLI_MODEL;
                empty means the subscription default)
            timeout: Seconds before the CLI process is killed
                (defaults to settings.CLAUDE_CLI_TIMEOUT)
            reference: Reference service for element names and examples
                (defaults to the shared singleton)
        """
        super().__init__(api_key="", model="", reference=reference)
        self.cli_path = cli_path or settings.CLAUDE_CLI_PATH
        self.cli_model = settings.CLAUDE_CLI_MODEL if model is None else model
        self.timeout = float(timeout or settings.CLAUDE_CLI_TIMEOUT)

    def _find_cli(self) -> Optional[str]:
        """
        Resolve the CLI executable.

        Returns:
            Absolute path to the executable, or None if it is not found
        """
        return shutil.which(self.cli_path)

    @property
    def is_configured(self) -> bool:
        """
        Whether AI analysis can run.

        Returns:
            True when AI is enabled and the CLI executable is found
        """
        if not settings.AI_ENABLED:
            return False
        return self._find_cli() is not None

    def _build_command(self, executable: str) -> List[str]:
        """
        Build the CLI command line.

        User and project settings, hooks, CLAUDE.md, plugins and MCP servers
        are disabled so the user's Claude Code customizations cannot change
        the answer. Only the Read tool is available, and only for files in
        the working directory: --restricted confines file tools to the
        working directories and ignores user, project and local settings
        files, and the permission rule allows Read only under "./".

        Args:
            executable: Resolved CLI path

        Returns:
            Argument list for subprocess
        """
        command = [
            executable,
            "-p",
            "--output-format", "json",
            "--restricted",
            "--safe-mode",
            "--strict-mcp-config",
            "--disable-slash-commands",
            "--no-session-persistence",
            "--tools", "Read",
            "--allowedTools", READ_RULE,
            "--permission-mode", "dontAsk",
            "--system-prompt", CLI_SYSTEM_PROMPT,
        ]
        if self.cli_model:
            command += ["--model", self.cli_model]
        return command

    @staticmethod
    def _child_env() -> Dict[str, str]:
        """
        Build the environment for the CLI process.

        Returns:
            Copy of os.environ without API credentials and parent session vars
        """
        env = {k: v for k, v in os.environ.items() if k not in STRIPPED_ENV_VARS}
        env["PYTHONIOENCODING"] = "utf-8"
        return env

    @staticmethod
    def _stage_frames(frames: List[str], work_dir: Path) -> List[str]:
        """
        Copy frames into the work directory under ASCII numbered names.

        Keeps the image order of the prompt, avoids Cyrillic in paths
        passed to the CLI, and keeps every file inside the CLI working
        directory.

        Args:
            frames: Paths to image frames, in prompt order
            work_dir: Temporary directory used as the CLI cwd

        Returns:
            Absolute paths of the copies, in the same order

        Raises:
            RuntimeError: If a frame cannot be copied
        """
        staged: List[str] = []
        for index, frame_path in enumerate(frames, start=1):
            suffix = Path(frame_path).suffix.lower() or ".jpg"
            target = work_dir / f"image_{index:02d}{suffix}"
            try:
                shutil.copyfile(frame_path, target)
            except OSError as exc:
                raise RuntimeError(f"Failed to stage frame {index}: {exc}") from exc
            staged.append(str(target.resolve()))
        return staged

    @staticmethod
    def _build_cli_prompt(image_paths: List[str], prompt: str) -> str:
        """
        Prepend the numbered image list to the analysis prompt.

        Args:
            image_paths: Staged image paths, numbered from 1 in prompt order
            prompt: Analysis prompt built by ClaudeService

        Returns:
            Prompt text sent to the CLI
        """
        lines = [
            "Открой инструментом Read каждое изображение по порядку. "
            "Номера изображений ниже совпадают с нумерацией в задании.",
        ]
        lines += [f"Изображение {i}: {p}" for i, p in enumerate(image_paths, start=1)]
        return "\n".join(lines) + "\n\n" + prompt

    @staticmethod
    def _error_text(payload: Dict[str, Any], stderr: str) -> str:
        """
        Pick an error description from CLI output, for logs only.

        Args:
            payload: Decoded `--output-format json` result
            stderr: CLI standard error

        Returns:
            Description of at most 500 characters
        """
        text = str(payload.get("result") or payload.get("subtype") or "").strip()
        if not text:
            text = stderr.strip()
        return text[:500] or "unknown error"

    def _parse_output(self, stdout: str, stderr: str, returncode: int) -> str:
        """
        Extract the model answer from `--output-format json` output.

        Exception messages stay short because they reach the user through
        analysis.error_message; raw CLI output goes to the warning log.

        Args:
            stdout: CLI standard output
            stderr: CLI standard error
            returncode: CLI exit code

        Returns:
            Text of the model answer

        Raises:
            ClaudeUnavailableError: If the CLI reports an error or limit
        """
        payload: Optional[Dict[str, Any]] = None
        try:
            decoded = json.loads(stdout)
            if isinstance(decoded, dict):
                payload = decoded
        except (json.JSONDecodeError, TypeError):
            payload = None

        if payload is None:
            logger.warning(
                "Claude CLI returned no JSON result (exit code %d): %s",
                returncode, (stderr or stdout or "").strip()[:500]
            )
            raise ClaudeUnavailableError(
                f"Claude CLI returned no JSON result (exit code {returncode})"
            )

        if payload.get("is_error") or returncode != 0:
            detail = self._error_text(payload, stderr)
            logger.warning("Claude CLI failed (exit code %d): %s", returncode, detail)
            if any(marker in detail.lower() for marker in LIMIT_MARKERS):
                raise ClaudeUnavailableError("Claude subscription limit reached")
            raise ClaudeUnavailableError(
                f"Claude CLI failed (exit code {returncode})"
            )

        result = payload.get("result")
        if not isinstance(result, str) or not result.strip():
            raise ClaudeUnavailableError("Claude CLI returned an empty result")
        return self._extract_json_text(result)

    @staticmethod
    def _extract_json_text(text: str) -> str:
        """
        Cut the JSON object out of an answer with leading or trailing prose.

        Answers that already start with "{" or a code fence are returned
        unchanged; ClaudeService.analyze_video strips the fences.

        Args:
            text: Model answer

        Returns:
            Text that starts with the JSON object when one is found
        """
        stripped = text.strip()
        if stripped.startswith("{") or stripped.startswith("```"):
            return stripped
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end > start:
            return stripped[start:end + 1]
        return stripped

    @staticmethod
    def _kill_tree(process: subprocess.Popen) -> None:
        """
        Kill the CLI process together with its child processes.

        Args:
            process: Running CLI process
        """
        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/T", "/F", "/PID", str(process.pid)],
                    capture_output=True,
                    timeout=KILL_WAIT_SECONDS,
                    shell=False,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                logger.warning("taskkill failed for Claude CLI: %s", exc)
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.communicate(timeout=KILL_WAIT_SECONDS)
        except (OSError, ValueError, subprocess.SubprocessError):
            pass

    def _run_cli(
        self,
        command: List[str],
        cli_prompt: str,
        work_dir: Path
    ) -> Tuple[str, str, int]:
        """
        Run the CLI and wait for it, killing the process tree on timeout.

        Any interruption (including Celery SoftTimeLimitExceeded) also kills
        the process tree before propagating.

        Args:
            command: CLI argument list
            cli_prompt: Prompt passed on stdin
            work_dir: CLI working directory

        Returns:
            (stdout, stderr, exit code)

        Raises:
            ClaudeUnavailableError: If the CLI cannot start or times out
        """
        creationflags = (
            subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        )
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(work_dir),
                env=self._child_env(),
                creationflags=creationflags,
                shell=False,
            )
        except OSError as exc:
            logger.warning("Claude CLI could not be started: %s", exc)
            raise ClaudeUnavailableError("Claude CLI could not be started") from exc

        try:
            stdout, stderr = process.communicate(input=cli_prompt, timeout=self.timeout)
        except subprocess.TimeoutExpired as exc:
            self._kill_tree(process)
            raise ClaudeUnavailableError(
                f"Claude CLI timed out after {self.timeout:.0f}s"
            ) from exc
        except BaseException:
            self._kill_tree(process)
            raise
        return stdout or "", stderr or "", process.returncode

    def _request(self, frames: List[str], prompt: str) -> str:
        """
        Run the Claude Code CLI on the frames and prompt.

        Args:
            frames: Paths to image frames (user frames first, then examples)
            prompt: Analysis prompt

        Returns:
            Raw text of the model response

        Raises:
            ClaudeUnavailableError: If the CLI is missing, times out, fails,
                or the subscription limit is reached
            RuntimeError: If a frame cannot be staged
        """
        executable = self._find_cli()
        if executable is None:
            logger.warning("Claude CLI not found: %s", self.cli_path)
            raise ClaudeUnavailableError("Claude CLI not found")

        # Cleanup errors (files still locked on Windows) must not fail the task
        with tempfile.TemporaryDirectory(
            prefix="hustl_cli_", ignore_cleanup_errors=True
        ) as tmp:
            work_dir = Path(tmp)
            image_paths = self._stage_frames(frames, work_dir)
            cli_prompt = self._build_cli_prompt(image_paths, prompt)
            command = self._build_command(executable)

            started = time.monotonic()
            logger.info(
                "Claude CLI request: %d images, prompt %d chars",
                len(image_paths), len(cli_prompt)
            )
            stdout, stderr, returncode = self._run_cli(command, cli_prompt, work_dir)
            logger.info(
                "Claude CLI finished in %.1fs, exit code %d, stdout %d chars",
                time.monotonic() - started, returncode, len(stdout)
            )
            return self._parse_output(stdout, stderr, returncode)

# Singleton, created lazily so importing this module never runs the CLI
_claude_cli_service: Optional[ClaudeCliService] = None


def get_claude_cli_service() -> ClaudeCliService:
    """
    Get the Claude CLI service singleton.

    Returns:
        ClaudeCliService instance
    """
    global _claude_cli_service
    if _claude_cli_service is None:
        _claude_cli_service = ClaudeCliService()
    return _claude_cli_service
