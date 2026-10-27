"""
Z.ai GLM API service for posture/technique/musicality analysis.

Reuses the prompt, response parsing and normalization of ClaudeService
and only swaps the transport: GLM exposes an OpenAI-compatible
chat completions endpoint.
"""

import httpx
import time
from typing import Dict, List, Any, Optional

from app.config import settings
from app.services.claude_service import (
    ClaudeService,
    ClaudeUnavailableError,
    PLACEHOLDER_KEY_MARKER,
)
from app.services.reference_service import ReferenceService


class GLMService(ClaudeService):
    """Service for GLM vision model dance analysis."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        reference: Optional[ReferenceService] = None
    ):
        """
        Initialize GLM service.

        Args:
            api_key: Z.ai API key (defaults to settings.GLM_API_KEY)
            model: Model ID (defaults to settings.GLM_MODEL)
            base_url: API base URL (defaults to settings.GLM_BASE_URL)
            reference: Reference service for element names and examples
                (defaults to the shared singleton)
        """
        super().__init__(
            api_key=api_key or settings.GLM_API_KEY,
            model=model or settings.GLM_MODEL,
            reference=reference
        )
        self.base_url = (base_url or settings.GLM_BASE_URL).rstrip("/")
        self.timeout = 180.0
        self.max_attempts = 4
        self.retry_delay = 10.0

    @property
    def is_configured(self) -> bool:
        """
        Whether AI analysis can run.

        Returns:
            True when AI is enabled, the API key is real, and a model is set
        """
        if not settings.AI_ENABLED:
            return False
        if not self.api_key or PLACEHOLDER_KEY_MARKER in self.api_key:
            return False
        return bool(self._model)

    def _request(self, frames: List[str], prompt: str) -> str:
        """
        Send frames and prompt to GLM chat completions.

        Args:
            frames: Paths to image frames
            prompt: Analysis prompt

        Returns:
            Raw text of the model response

        Raises:
            ClaudeUnavailableError: If no model is configured
            RuntimeError: If the API call fails
        """
        if not self._model:
            raise ClaudeUnavailableError("GLM_MODEL is not configured")

        content: List[Dict[str, Any]] = []
        for frame_path in frames:
            data = self.encode_image(frame_path)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{self.media_type(frame_path)};base64,{data}"
                }
            })

        content.append({"type": "text", "text": prompt})

        payload = {
            "model": self._model,
            "max_tokens": 4000,
            "messages": [{"role": "user", "content": content}],
            # Analysis needs a plain JSON answer, not reasoning traces
            "thinking": {"type": "disabled"},
        }

        try:
            response = self._post_with_retry(payload)
            response.raise_for_status()
            message = response.json()["choices"][0]["message"]
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"GLM API call failed: {exc.response.status_code} "
                f"{exc.response.text[:500]}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"GLM API call failed: {exc}") from exc

        response_content = message.get("content") or ""
        if isinstance(response_content, list):
            response_content = "".join(
                part.get("text", "") for part in response_content
                if isinstance(part, dict)
            )
        return response_content

    def _post_with_retry(self, payload: Dict[str, Any]) -> httpx.Response:
        """
        POST to chat completions, retrying on overload and server errors.

        Free GLM models often answer 429 "temporarily overloaded", so
        transient failures are retried with a linear backoff.

        Args:
            payload: Request body

        Returns:
            Last HTTP response
        """
        response: Optional[httpx.Response] = None
        for attempt in range(1, self.max_attempts + 1):
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=self.timeout
            )
            transient = response.status_code >= 500 or (
                response.status_code == 429 and '"1113"' not in response.text
            )
            if not transient or attempt == self.max_attempts:
                break
            time.sleep(self.retry_delay * attempt)
        return response


# Singleton, created lazily so importing this module never requires a key
_glm_service: Optional[GLMService] = None


def get_glm_service() -> GLMService:
    """
    Get the GLM service singleton.

    Returns:
        GLMService instance
    """
    global _glm_service
    if _glm_service is None:
        _glm_service = GLMService()
    return _glm_service
