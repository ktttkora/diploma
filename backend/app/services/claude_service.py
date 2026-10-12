"""
Claude API service for posture/technique/musicality analysis.

Sends video frames plus local rhythm data to Claude and parses the
structured JSON response.
"""

import anthropic
import base64
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

from app.config import settings


ANALYSIS_PROMPT = """Ты - эксперт по технике танца хастл. Проанализируй кадры танцевального видео.

ДАННЫЕ О РИТМЕ (локальный анализ):
{rhythm_data}

ЗАДАЧА:
1. Определи, какие элементы хастла выполняются (Американка, Солнышко, Катапульта, Йо-йо, Окошко, Свечка, Лодочка, Смена мест, Повороты, или базовые шаги)
2. Оцени ПОСТУРУ: положение спины, плеч, рук, головы (0-100)
3. Оцени ТЕХНИКУ: правильность выполнения элементов, работа ног, ведение/следование (0-100)
4. Оцени МУЗЫКАЛЬНОСТЬ: выразительность, использование акцентов, соответствие характеру музыки (0-100)
5. Найди до 10 самых значимых ошибок

ФОРМАТ ОТВЕТА (строго JSON):
{{
  "detected_elements": ["элемент1", "элемент2"],
  "posture_score": 75,
  "technique_score": 70,
  "musicality_score": 80,
  "errors": [
    {{
      "timestamp": 12.5,
      "category": "posture",
      "severity": "high",
      "title": "Сутулая спина",
      "description": "На 12.5с спина согнута, плечи опущены вперёд",
      "recommendation": "Держите спину прямо, сведите лопатки, поднимите подбородок",
      "detected_element": "Американка"
    }}
  ]
}}

Категории ошибок: posture, technique, musicality
Серьёзность: low, medium, high, critical

Отвечай ТОЛЬКО JSON, без дополнительного текста."""

VALID_CATEGORIES = {"posture", "technique", "musicality"}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}

# Shown to the user when AI analysis is unavailable
PLACEHOLDER_KEY_MARKER = "your-key-here"


class ClaudeUnavailableError(RuntimeError):
    """Raised when AI analysis cannot run (missing key or model)."""


class ClaudeService:
    """Service for Claude API dance analysis."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Claude service.

        Args:
            api_key: Anthropic API key (defaults to settings)
            model: Model ID (defaults to settings.CLAUDE_MODEL)
        """
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self._model = model or settings.CLAUDE_MODEL
        self._client: Optional[anthropic.Anthropic] = None
        self.max_frames = 20  # Limit frames per request

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
        return True

    @property
    def client(self) -> anthropic.Anthropic:
        """Lazily create the Anthropic client."""
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def _resolve_model(self) -> str:
        """
        Pick the model to use.

        Uses the configured model when set; otherwise asks the API for the
        available models and takes the newest one.

        Returns:
            Model ID

        Raises:
            ClaudeUnavailableError: If no model can be determined
        """
        if self._model:
            return self._model

        try:
            models = list(self.client.models.list(limit=1))
        except Exception as exc:
            raise ClaudeUnavailableError(
                f"No CLAUDE_MODEL configured and the model list is unavailable: {exc}"
            ) from exc

        if not models:
            raise ClaudeUnavailableError("No models available for this API key")

        self._model = models[0].id
        return self._model

    def encode_image(self, image_path: str) -> str:
        """
        Encode an image file to base64.

        Args:
            image_path: Path to image file

        Returns:
            Base64-encoded image data
        """
        with open(image_path, "rb") as f:
            return base64.standard_b64encode(f.read()).decode("utf-8")

    def _build_rhythm_summary(
        self,
        rhythm_errors: List[Dict[str, Any]],
        tempo: Optional[float] = None
    ) -> str:
        """
        Build the rhythm section of the prompt.

        Args:
            rhythm_errors: Errors from local rhythm analysis
            tempo: Music tempo in BPM

        Returns:
            Human-readable rhythm summary
        """
        summary = f"Темп: {tempo:.0f} BPM. " if tempo else ""

        if rhythm_errors:
            summary += f"Найдено {len(rhythm_errors)} ошибок ритма: "
            summary += "; ".join(
                f"{e.get('timestamp', '?')}с - {e.get('title', '?')}"
                for e in rhythm_errors[:5]
            )
        else:
            summary += "Ошибок ритма не найдено."

        return summary

    def analyze_video(
        self,
        frame_paths: List[str],
        rhythm_errors: List[Dict[str, Any]],
        tempo: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Analyze dance video frames with Claude.

        Args:
            frame_paths: Paths to JPEG frames
            rhythm_errors: Rhythm errors from local analysis
            tempo: Music tempo in BPM

        Returns:
            Dict with detected_elements, posture_score, technique_score,
            musicality_score, and errors

        Raises:
            ClaudeUnavailableError: If AI analysis is not configured
            RuntimeError: If the API call fails or the response cannot be parsed
        """
        if not self.is_configured:
            raise ClaudeUnavailableError("AI analysis is not configured")

        frames = frame_paths[:self.max_frames]
        if not frames:
            raise RuntimeError("No frames provided for analysis")

        prompt = ANALYSIS_PROMPT.format(
            rhythm_data=self._build_rhythm_summary(rhythm_errors, tempo)
        )

        content: List[Dict[str, Any]] = []
        for frame_path in frames:
            extension = Path(frame_path).suffix.lower()
            media_type = "image/png" if extension == ".png" else "image/jpeg"
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": self.encode_image(frame_path)
                }
            })

        content.append({"type": "text", "text": prompt})

        try:
            message = self.client.messages.create(
                model=self._resolve_model(),
                max_tokens=4000,
                messages=[{"role": "user", "content": content}]
            )
        except ClaudeUnavailableError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Claude API call failed: {exc}") from exc

        response_text = "".join(
            block.text for block in message.content if getattr(block, "text", None)
        ).strip()

        # Strip markdown code fences if the model wrapped the JSON
        if response_text.startswith("```"):
            lines = [
                line for line in response_text.split("\n")
                if not line.strip().startswith("```")
            ]
            response_text = "\n".join(lines).strip()

        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Failed to parse Claude response as JSON: {exc}"
            ) from exc

        return self._normalize(parsed)

    def _normalize(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coerce a parsed AI response into the expected shape.

        The model occasionally returns scores as strings, unknown categories,
        or timestamps outside the video, so each field is clamped here.

        Args:
            parsed: Raw parsed JSON from the model

        Returns:
            Normalized analysis dict
        """
        def clamp_score(value: Any) -> Optional[float]:
            try:
                score = float(value)
            except (TypeError, ValueError):
                return None
            return max(0.0, min(100.0, score))

        errors = []
        for raw in parsed.get("errors", []) or []:
            if not isinstance(raw, dict):
                continue

            category = str(raw.get("category", "technique")).lower()
            severity = str(raw.get("severity", "medium")).lower()

            try:
                timestamp = max(0.0, float(raw.get("timestamp", 0)))
            except (TypeError, ValueError):
                timestamp = 0.0

            errors.append({
                "timestamp": timestamp,
                "category": category if category in VALID_CATEGORIES else "technique",
                "severity": severity if severity in VALID_SEVERITIES else "medium",
                "title": str(raw.get("title", "")).strip() or "Ошибка техники",
                "description": str(raw.get("description", "")).strip(),
                "recommendation": str(raw.get("recommendation", "")).strip(),
                "detected_element": raw.get("detected_element") or None,
            })

        detected = parsed.get("detected_elements") or []
        if not isinstance(detected, list):
            detected = []

        return {
            "detected_elements": [str(e) for e in detected],
            "posture_score": clamp_score(parsed.get("posture_score")),
            "technique_score": clamp_score(parsed.get("technique_score")),
            "musicality_score": clamp_score(parsed.get("musicality_score")),
            "errors": errors,
        }


# Singleton, created lazily so importing this module never requires a key
_claude_service: Optional[ClaudeService] = None


def get_claude_service() -> ClaudeService:
    """
    Get the Claude service singleton.

    Returns:
        ClaudeService instance
    """
    global _claude_service
    if _claude_service is None:
        _claude_service = ClaudeService()
    return _claude_service
