"""
Claude API service for posture/technique/musicality analysis.

Sends video frames plus local rhythm data to Claude and parses the
structured JSON response.
"""

import anthropic
import base64
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from app.config import settings
from app.services.reference_service import ReferenceService, PASSTHROUGH_EXCEPTIONS

logger = logging.getLogger(__name__)


def _is_readable_file(path: str) -> bool:
    """Whether an image path exists, is non-empty and can be opened."""
    try:
        with open(path, "rb") as f:
            return bool(f.read(1))
    except OSError:
        return False


ANALYSIS_PROMPT = """Ты - эксперт по технике танца хастл. Проанализируй кадры танцевального видео.
{images_section}
ДАННЫЕ О РИТМЕ (локальный анализ):
{rhythm_data}
{elements_section}
ЗАДАЧА:
1. {elements_task}
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

DEFAULT_ELEMENTS_TASK = (
    "Определи, какие элементы хастла выполняются (Американка, Солнышко, "
    "Катапульта, Йо-йо, Окошко, Свечка, Лодочка, Смена мест, Повороты, "
    "или базовые шаги)"
)

CATALOG_ELEMENTS_TASK = (
    "Определи, какие элементы хастла выполняются. В detected_elements и "
    "detected_element пиши названия ТОЛЬКО из списка ЭЛЕМЕНТЫ, дословно. "
    "Если элемент не из списка или не распознан, detected_element = null"
)

VALID_CATEGORIES = {"posture", "technique", "musicality"}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}

# Shown to the user when AI analysis is unavailable
PLACEHOLDER_KEY_MARKER = "your-key-here"


class ClaudeUnavailableError(RuntimeError):
    """Raised when AI analysis cannot run (missing key or model)."""


class ClaudeService:
    """Service for Claude API dance analysis."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        reference: Optional[ReferenceService] = None
    ):
        """
        Initialize Claude service.

        Args:
            api_key: Anthropic API key (defaults to settings)
            model: Model ID (defaults to settings.CLAUDE_MODEL)
            reference: Reference service for element names and examples
                (defaults to the shared singleton)
        """
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self._model = model or settings.CLAUDE_MODEL
        self._client: Optional[anthropic.Anthropic] = None
        self.max_frames = 20  # Limit frames per request
        self._reference = reference

    @property
    def reference(self) -> ReferenceService:
        """Reference service used for element names and examples."""
        if self._reference is None:
            from app.services.reference_service import reference_service
            self._reference = reference_service
        return self._reference

    @reference.setter
    def reference(self, value: ReferenceService) -> None:
        """Replace the reference service (used by tests)."""
        self._reference = value

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
            kwargs: Dict[str, Any] = {"api_key": self.api_key}
            if settings.ANTHROPIC_BASE_URL:
                kwargs["base_url"] = settings.ANTHROPIC_BASE_URL
            self._client = anthropic.Anthropic(**kwargs)
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

    def _load_element_catalog(self) -> Dict[str, str]:
        """
        Load reference element names, never failing the analysis.

        Returns:
            Catalog {display_name: stem}, or {} if references are unavailable
        """
        try:
            return self.reference.get_element_catalog()
        except PASSTHROUGH_EXCEPTIONS:
            raise
        except Exception as exc:
            logger.warning("Reference element list unavailable: %s", exc)
            return {}

    def _select_examples(
        self,
        user_poses: Optional[List[Dict[str, Any]]],
        budget: int,
        user_aspect: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Pick reference example frames, never failing the analysis.

        Frames that are missing or unreadable are dropped here, because
        image encoding in _request is not guarded and would fail the whole
        AI call. Celery time limits are re-raised.

        Args:
            user_poses: Poses of the user video (None disables examples)
            budget: Maximum number of example images
            user_aspect: Frame width / height of the user video

        Returns:
            List of {element, frame_paths, ...}, or [] on any failure
        """
        if not settings.AI_REFERENCE_EXAMPLES or not user_poses or budget <= 0:
            return []
        try:
            examples = self.reference.select_example_frames(
                user_poses,
                max_images=budget,
                max_elements=settings.AI_REFERENCE_CANDIDATES,
                frames_per_element=settings.AI_REFERENCE_FRAMES_PER_ELEMENT,
                max_side=settings.AI_REFERENCE_FRAME_MAX_SIDE,
                user_aspect=user_aspect,
            )
        except PASSTHROUGH_EXCEPTIONS:
            raise
        except Exception as exc:
            logger.warning("Reference example selection failed: %s", exc)
            return []

        readable: List[Dict[str, Any]] = []
        for example in examples:
            paths = [p for p in example.get("frame_paths", []) if _is_readable_file(p)]
            if len(paths) != len(example.get("frame_paths", [])):
                logger.warning("Dropped unreadable example frames for %s", example.get("element"))
            if paths:
                readable.append({**example, "frame_paths": paths})
        return readable

    @staticmethod
    def _build_reference_sections(
        user_frame_count: int,
        catalog: Dict[str, str],
        examples: List[Dict[str, Any]]
    ) -> Tuple[str, str, str]:
        """
        Build the prompt parts that describe images and reference elements.

        Args:
            user_frame_count: Number of user frames sent first
            catalog: Element catalog {display_name: stem}
            examples: Selected examples, in the order their images are sent

        Returns:
            (images_section, elements_section, elements_task)
        """
        if not catalog:
            return "", "", DEFAULT_ELEMENTS_TASK

        elements_section = (
            "\nЭЛЕМЕНТЫ (допустимые названия): " + "; ".join(catalog) + "\n"
        )

        if not examples:
            return "", elements_section, CATALOG_ELEMENTS_TASK

        user_span = "1" if user_frame_count == 1 else f"1-{user_frame_count}"
        lines = [
            "",
            f"ИЗОБРАЖЕНИЯ: {user_span} - кадры видео пользователя, "
            "анализируй и оценивай только их.",
            "Остальные изображения - эталонные кадры элементов, наиболее похожих "
            "по позам. Используй их только для распознавания элементов, "
            "ошибки по ним не ищи:",
        ]
        position = user_frame_count + 1
        for example in examples:
            count = len(example["frame_paths"])
            span = str(position) if count == 1 else f"{position}-{position + count - 1}"
            lines.append(f"- изображения {span}: {example['element']}")
            position += count
        return "\n".join(lines) + "\n", elements_section, CATALOG_ELEMENTS_TASK

    def _match_elements(
        self,
        result: Dict[str, Any],
        catalog: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Map element names in a normalized AI result onto the catalog.

        Unknown names become None (detected_element) or are dropped
        (detected_elements). Without a catalog the result is unchanged.

        Args:
            result: Output of _normalize
            catalog: Element catalog {display_name: stem}

        Returns:
            The same dict with matched element names
        """
        if not catalog:
            return result

        matched: List[str] = []
        for name in result.get("detected_elements", []):
            display = self.reference.match_element_name(name, catalog)
            if display and display not in matched:
                matched.append(display)
        result["detected_elements"] = matched

        for err in result.get("errors", []):
            raw = err.get("detected_element")
            err["detected_element"] = (
                self.reference.match_element_name(raw, catalog) if raw else None
            )
        return result

    def analyze_video(
        self,
        frame_paths: List[str],
        rhythm_errors: List[Dict[str, Any]],
        tempo: Optional[float] = None,
        user_poses: Optional[List[Dict[str, Any]]] = None,
        user_aspect: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Analyze dance video frames with the AI model.

        The prompt lists every available reference element; when user poses
        are given, example frames of the most similar reference elements are
        appended after the user frames. Reference failures only log a warning.

        Args:
            frame_paths: Paths to JPEG frames
            rhythm_errors: Rhythm errors from local analysis
            tempo: Music tempo in BPM
            user_poses: MediaPipe poses of the user video, for example selection
            user_aspect: Frame width / height of the user video, needed to
                compare poses with references of another orientation

        Returns:
            Dict with detected_elements, posture_score, technique_score,
            musicality_score, and errors

        Raises:
            ClaudeUnavailableError: If AI analysis is not configured
            RuntimeError: If the API call fails or the response cannot be parsed
        """
        if not self.is_configured:
            raise ClaudeUnavailableError("AI analysis is not configured")

        max_images = max(1, settings.AI_MAX_IMAGES)
        frames = frame_paths[:min(self.max_frames, max_images)]
        if not frames:
            raise RuntimeError("No frames provided for analysis")

        catalog = self._load_element_catalog()
        examples = (
            self._select_examples(user_poses, max_images - len(frames), user_aspect)
            if catalog else []
        )
        images_section, elements_section, elements_task = (
            self._build_reference_sections(len(frames), catalog, examples)
        )

        prompt = ANALYSIS_PROMPT.format(
            images_section=images_section,
            rhythm_data=self._build_rhythm_summary(rhythm_errors, tempo),
            elements_section=elements_section,
            elements_task=elements_task,
        )

        example_frames = [p for e in examples for p in e["frame_paths"]]
        response_text = self._request(frames + example_frames, prompt).strip()

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
                f"Failed to parse AI response as JSON: {exc}"
            ) from exc

        return self._match_elements(self._normalize(parsed), catalog)

    @staticmethod
    def media_type(frame_path: str) -> str:
        """
        Guess the image media type from the file extension.

        Args:
            frame_path: Path to image file

        Returns:
            MIME type of the image
        """
        extension = Path(frame_path).suffix.lower()
        return "image/png" if extension == ".png" else "image/jpeg"

    def _request(self, frames: List[str], prompt: str) -> str:
        """
        Send frames and prompt to Claude.

        Args:
            frames: Paths to image frames
            prompt: Analysis prompt

        Returns:
            Raw text of the model response

        Raises:
            ClaudeUnavailableError: If no model can be determined
            RuntimeError: If the API call fails
        """
        content: List[Dict[str, Any]] = []
        for frame_path in frames:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": self.media_type(frame_path),
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

        return "".join(
            block.text for block in message.content if getattr(block, "text", None)
        )

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


def get_ai_service() -> ClaudeService:
    """
    Get the AI service selected by settings.AI_PROVIDER.

    Returns:
        ClaudeService or GLMService instance
    """
    if settings.AI_PROVIDER == "glm":
        from app.services.glm_service import get_glm_service
        return get_glm_service()
    return get_claude_service()
