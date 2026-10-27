"""
Rhythm analysis service.

Combines audio beat detection (librosa) with pose-based step detection
(MediaPipe) to evaluate dance rhythm accuracy.
"""

import os
import tempfile
from typing import Dict, List, Any, Optional

from app.services.audio_service import audio_service
from app.services.pose_service import pose_service
from app.utils.video_utils import extract_audio, validate_video


class RhythmService:
    """Service for local rhythm analysis."""

    def __init__(self, beat_tolerance: float = 0.15):
        """
        Initialize rhythm service.

        Args:
            beat_tolerance: Allowed deviation from beat in seconds
        """
        self.beat_tolerance = beat_tolerance

    def analyze_rhythm(self, video_path: str) -> Dict[str, Any]:
        """
        Full rhythm analysis pipeline.

        1. Validate video
        2. Extract audio (FFmpeg)
        3. Detect beats (librosa)
        4. Extract poses (MediaPipe)
        5. Detect steps
        6. Match steps to beats
        7. Calculate score and errors

        Args:
            video_path: Path to video file

        Returns:
            Dict with tempo, total_beats, total_steps, accuracy,
            rhythm_score, errors, poses (MediaPipe poses of every frame,
            reused for reference element matching) and video_aspect
            (frame width / height, needed to compare those poses)

        Raises:
            RuntimeError: If any pipeline step fails
        """
        # 1. Validate
        validation = validate_video(video_path)
        video_info = validation["info"]

        # 2. Extract audio to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            audio_path = tmp.name

        try:
            extract_audio(video_path, audio_path)

            # 3. Analyze audio
            audio_result = audio_service.analyze_audio(audio_path)
            beats = audio_result["beats"]
            tempo = audio_result["tempo"]

            # 4. Extract poses
            poses = pose_service.extract_poses_from_video(video_path)

            # 5. Detect steps
            steps = pose_service.detect_steps(poses)
            step_times = [s["timestamp"] for s in steps]

            # 6. Match steps to beats
            rhythm_stats = audio_service.calculate_rhythm_accuracy(
                step_times, beats, self.beat_tolerance
            )

            # 7. Calculate score (0-100)
            rhythm_score = rhythm_stats["accuracy"]

            # Build error list for off-beat steps (limit to 10)
            errors = []
            for off_step in rhythm_stats["off_beat_steps"][:10]:
                errors.append({
                    "timestamp": off_step["timestamp"],
                    "category": "rhythm",
                    "severity": "medium" if off_step["deviation"] < 0.3 else "high",
                    "title": "Шаг не в бит",
                    "description": f"Шаг на {off_step['timestamp']:.2f}с отклоняется от бита на {off_step['deviation']:.2f}с",
                    "recommendation": "Слушайте бит музыки и старайтесь попадать шагом точно в удар",
                    "detected_element": None
                })

            return {
                "tempo": tempo,
                "total_beats": audio_result["total_beats"],
                "total_steps": rhythm_stats["total"],
                "steps_on_beat": rhythm_stats["on_beat"],
                "accuracy": rhythm_stats["accuracy"],
                "rhythm_score": round(rhythm_score, 1),
                "duration": audio_result["duration"],
                "video_duration": video_info["duration"],
                "errors": errors,
                # Reused for reference element matching, so MediaPipe runs once
                "poses": poses,
                "video_aspect": self._video_aspect(video_path, video_info)
            }

        finally:
            # Cleanup temp audio
            if os.path.exists(audio_path):
                os.unlink(audio_path)

    @staticmethod
    def _video_aspect(video_path: str, video_info: Dict[str, Any]) -> Optional[float]:
        """
        Frame width / height of the video as MediaPipe sees it.

        Reads a decoded frame (handles rotated phone videos), falling back
        to the width/height reported by ffprobe.

        Args:
            video_path: Path to video file
            video_info: Info from validate_video

        Returns:
            Aspect ratio, or None if unknown
        """
        from app.services.reference_service import PASSTHROUGH_EXCEPTIONS, get_video_aspect

        try:
            aspect = get_video_aspect(video_path)
        except PASSTHROUGH_EXCEPTIONS:
            raise
        except Exception:
            aspect = None
        if aspect:
            return aspect

        width = video_info.get("width") or 0
        height = video_info.get("height") or 0
        return float(width) / float(height) if width and height else None


# Singleton instance
rhythm_service = RhythmService()
