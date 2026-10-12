"""
Claude API service for posture/technique/musicality analysis.

Sends video frames + rhythm data to Claude for AI-powered dance analysis.
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


class ClaudeService:
    """Service for Claude API dance analysis."""

    # Claude model for vision analysis
    MODEL = "claude-opus-5-5"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Claude service.

        Args:
            api_key: Anthropic API key (defaults to settings)
        """
        self.client = anthropic.Anthropic(api_key=api_key or settings.ANTHROPIC_API_KEY)
        self.max_frames = 20  # Limit frames per request

    def encode_image(self, image_path: str) -> str:
        """
        Encode image file to base64.

        Args:
            image_path: Path to image file

        Returns:
            Base64-encoded image string
        """
        with open(image_path, "rb") as f:
            return base64.standard_b64encode(f.read()).decode("utf-8")

    def analyze_video(
        self,
        frame_paths: List[str],
        rhythm_errors: List[Dict[str, Any]],
        tempo: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Analyze dance video frames with Claude.

        Args:
            frame_paths: List of paths to JPEG frames (max 20)
            rhythm_errors: Rhythm errors from local analysis
            tempo: Music tempo BPM

        Returns:
            Dict with detected_elements, posture_score, technique_score,
            musicality_score, errors

        Raises:
            RuntimeError: If Claude API call fails
        """
        # Limit frames
        frames = frame_paths[:self.max_frames]

        # Build rhythm summary
        rhythm_summary = f"Темп: {tempo} BPM. " if tempo else ""
        if rhythm_errors:
            rhythm_summary += f"Найдено {len(rhythm_errors)} ошибок ритма: "
            rhythm_summary += "; ".join(
                f"{e.get('timestamp', '?')}с - {e.get('title', '?')}"
                for e in rhythm_errors[:5]
            )
        else:
            rhythm_summary += "Ошибок ритма не найдено."

        prompt = ANALYSIS_PROMPT.format(rhythm_data=rhythm_summary)

        # Build message content with images
        content = []
        for frame_path in frames:
            image_data = self.encode_image(frame_path)
            ext = Path(frame_path).suffix.lower()
            media_type = "image/png" if ext == ".png" else "image/jpeg"
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_data
                }
            })

        content.append({"type": "text", "text": prompt})

        try:
            message = self.client.messages.create(
                model=self.MODEL,
                max_tokens=4000,
                messages=[{"role": "user", "content": content}]
            )

            # Parse response
            response_text = message.content[0].text.strip()

            # Remove markdown code fences if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                response_text = "\n".join(lines)

            return json.loads(response_text)

        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse Claude response as JSON: {e}")
        except Exception as e:
            raise RuntimeError(f"Claude API call failed: {e}")


# Singleton instance (lazy - created on first use to avoid API key validation at import)
_claude_service: Optional[ClaudeService] = None


def get_claude_service() -> ClaudeService:
    """Get or create Claude service singleton."""
    global _claude_service
    if _claude_service is None:
        _claude_service = ClaudeService()
    return _claude_service
