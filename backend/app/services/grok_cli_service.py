"""
Grok CLI service for posture, technique and musicality analysis.

Uses the local `grok` command signed in with `grok login`. API keys and
custom base URLs are removed from the child environment, so the call
follows the subscription rather than a key or a fixed address.
"""

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.services.claude_cli_service import ClaudeCliService
from app.services.claude_service import ClaudeUnavailableError

logger = logging.getLogger(__name__)

GROK_SYSTEM_PROMPT = (
    "You are a dance technique analysis engine. The user message lists image "
    "files by number. Use the Read tool to view every listed image, in order, "
    "before answering. Do not use any other tool and do not ask questions. "
    "Your final answer must be ONLY the JSON object requested by the user "
    "message: no markdown, no code fences, no comments, no text before or "
    "after the JSON."
)

# These would switch the CLI off the subscription login onto a key or a
# caller-supplied address.
STRIPPED_ENV_VARS = (
    "XAI_API_KEY",
    "XAI_API_BASE_URL",
    "GROK_API_KEY",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "CLI_CHAT_PROXY_BASE_URL",
    "GROK_WS_URL",
    "GROK_WS_ORIGIN",
)

READ_RULE = "Read(./**)"
PROMPT_NAME = "prompt.txt"
# One turn to read each image, plus the final answer
EXTRA_TURNS = 4


class GrokCliService(ClaudeCliService):
    """Dance analysis through the local Grok CLI subscription."""

    def __init__(
        self,
        cli_path: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        reference: Optional[Any] = None
    ):
        """
        Initialize the Grok CLI service.

        Args:
            cli_path: CLI executable name or path
            model: Model id, empty means the subscription default
            timeout: Seconds before the process is killed
            reference: Reference service for element names and examples
        """
        super().__init__(
            cli_path=cli_path or settings.GROK_CLI_PATH,
            model="",
            timeout=timeout if timeout is not None else settings.GROK_CLI_TIMEOUT,
            reference=reference,
        )
        self.cli_model = settings.GROK_CLI_MODEL if model is None else model

    def _build_command(self, executable: str, prompt_path: Path, image_count: int) -> List[str]:
        """
        Build the headless Grok command.

        The prompt is a file because a Windows command line cannot hold
        the full analysis text. Only Read is offered, and only inside the
        working directory.

        Args:
            executable: Resolved CLI path
            prompt_path: Prompt file inside the working directory
            image_count: How many images the model must open

        Returns:
            Argument list for subprocess
        """
        command = [
            executable,
            "--prompt-file", str(prompt_path),
            "--output-format", "json",
            "--verbatim",
            "--no-subagents",
            "--disable-web-search",
            "--permission-mode", "dontAsk",
            "--tools", "Read",
            "--allow", READ_RULE,
            "--max-turns", str(image_count + EXTRA_TURNS),
            "--system-prompt-override", GROK_SYSTEM_PROMPT,
        ]
        if self.cli_model:
            command += ["--model", self.cli_model]
        return command

    @staticmethod
    def _child_env() -> Dict[str, str]:
        """
        Environment for the CLI, without API keys or custom addresses.

        Returns:
            Copy of os.environ that keeps the subscription login only
        """
        env = {k: v for k, v in os.environ.items() if k not in STRIPPED_ENV_VARS}
        env["PYTHONIOENCODING"] = "utf-8"
        return env

    def _parse_output(self, stdout: str, stderr: str, returncode: int) -> str:
        """
        Extract the model answer from `--output-format json`.

        Args:
            stdout: CLI standard output
            stderr: CLI standard error
            returncode: CLI exit code

        Returns:
            Text of the model answer

        Raises:
            ClaudeUnavailableError: If Grok reports an error or a limit
        """
        payload: Optional[Dict[str, Any]] = None
        try:
            decoded = json.loads(stdout)
            if isinstance(decoded, dict):
                payload = decoded
        except (json.JSONDecodeError, TypeError):
            payload = None

        if payload is None:
            detail = (stderr or stdout or "").strip()[:500]
            logger.warning(
                "Grok CLI returned no JSON result (exit code %d): %s",
                returncode, detail
            )
            if "not logged in" in detail.lower() or "sign in" in detail.lower():
                raise ClaudeUnavailableError("Grok CLI is not signed in. Run: grok login")
            raise ClaudeUnavailableError(
                f"Grok CLI returned no JSON result (exit code {returncode})"
            )

        text = payload.get("text")
        stop_reason = str(payload.get("stopReason") or "")
        if returncode != 0 or not isinstance(text, str) or not text.strip():
            detail = (text if isinstance(text, str) and text.strip() else stderr.strip())
            detail = (detail or stop_reason or "unknown error")[:500]
            logger.warning("Grok CLI failed (exit code %d): %s", returncode, detail)
            lowered = detail.lower()
            if any(marker in lowered for marker in ("usage limit", "rate limit", "limit reached", "quota")):
                raise ClaudeUnavailableError("Grok subscription limit reached")
            if "not logged in" in lowered or "sign in" in lowered or "login" in lowered:
                raise ClaudeUnavailableError("Grok CLI is not signed in. Run: grok login")
            raise ClaudeUnavailableError(
                f"Grok CLI failed (exit code {returncode})"
            )
        return self._extract_json_text(text)

    def _run_cli(
        self,
        command: List[str],
        work_dir: Path
    ) -> Tuple[str, str, int]:
        """
        Run Grok and wait, killing the process tree on timeout.

        Args:
            command: CLI argument list
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
                stdin=subprocess.DEVNULL,
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
            logger.warning("Grok CLI could not be started: %s", exc)
            raise ClaudeUnavailableError("Grok CLI could not be started") from exc

        try:
            stdout, stderr = process.communicate(timeout=self.timeout)
        except subprocess.TimeoutExpired as exc:
            self._kill_tree(process)
            raise ClaudeUnavailableError(
                f"Grok CLI timed out after {self.timeout:.0f}s"
            ) from exc
        except BaseException:
            self._kill_tree(process)
            raise
        return stdout or "", stderr or "", process.returncode

    def _request(self, frames: List[str], prompt: str) -> str:
        """
        Run Grok on the frames and prompt.

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
            logger.warning("Grok CLI not found: %s", self.cli_path)
            raise ClaudeUnavailableError("Grok CLI not found")

        import tempfile
        with tempfile.TemporaryDirectory(
            prefix="hustl_grok_", ignore_cleanup_errors=True
        ) as tmp:
            work_dir = Path(tmp)
            image_paths = self._stage_frames(frames, work_dir)
            prompt_path = work_dir / PROMPT_NAME
            prompt_path.write_text(
                self._build_cli_prompt(image_paths, prompt),
                encoding="utf-8",
            )
            command = self._build_command(executable, prompt_path, len(image_paths))
            started = time.monotonic()
            logger.info(
                "Grok CLI request: %d images, prompt %d chars",
                len(image_paths), prompt_path.stat().st_size
            )
            stdout, stderr, returncode = self._run_cli(command, work_dir)
            logger.info(
                "Grok CLI finished in %.1fs, exit code %d, stdout %d chars",
                time.monotonic() - started, returncode, len(stdout)
            )
            return self._parse_output(stdout, stderr, returncode)


_grok_cli_service: Optional[GrokCliService] = None


def get_grok_cli_service() -> GrokCliService:
    """
    Get the Grok CLI service singleton.

    Returns:
        GrokCliService instance
    """
    global _grok_cli_service
    if _grok_cli_service is None:
        _grok_cli_service = GrokCliService()
    return _grok_cli_service
