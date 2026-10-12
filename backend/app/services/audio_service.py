"""
Audio analysis service using librosa.

Extracts tempo, beats, and musical features from audio tracks.
"""

import librosa
import numpy as np
from typing import Dict, List, Tuple, Any


class AudioService:
    """Service for audio analysis using librosa."""

    def __init__(self, sample_rate: int = 22050):
        """
        Initialize audio service.

        Args:
            sample_rate: Target sample rate for audio loading
        """
        self.sample_rate = sample_rate

    def analyze_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Analyze audio file: tempo, beats, duration.

        Args:
            audio_path: Path to audio file (WAV recommended)

        Returns:
            Dict with tempo, beats, duration, sample_rate

        Raises:
            RuntimeError: If audio loading or analysis fails
        """
        try:
            # Load audio
            y, sr = librosa.load(audio_path, sr=self.sample_rate)

            if len(y) == 0:
                raise RuntimeError("Empty audio file")

            duration = float(librosa.get_duration(y=y, sr=sr))

            # Detect tempo and beats
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)

            # Convert beat frames to timestamps
            beat_times = librosa.frames_to_time(beats, sr=sr).tolist()

            # Onset strength for additional features
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            avg_onset = float(np.mean(onset_env))

            return {
                "tempo": float(tempo),
                "beats": [round(float(b), 3) for b in beat_times],
                "total_beats": len(beat_times),
                "duration": round(duration, 2),
                "sample_rate": int(sr),
                "avg_onset_strength": round(avg_onset, 4)
            }

        except Exception as e:
            raise RuntimeError(f"Audio analysis failed: {e}")

    def find_closest_beat(self, timestamp: float, beats: List[float]) -> Tuple[float, float]:
        """
        Find closest beat to given timestamp.

        Args:
            timestamp: Timestamp in seconds
            beats: List of beat timestamps

        Returns:
            Tuple of (closest_beat_time, difference_in_seconds)
        """
        if not beats:
            return 0.0, abs(timestamp)

        closest = min(beats, key=lambda b: abs(b - timestamp))
        return closest, abs(closest - timestamp)

    def is_on_beat(self, timestamp: float, beats: List[float], tolerance: float = 0.15) -> bool:
        """
        Check if timestamp falls on a beat within tolerance.

        Args:
            timestamp: Timestamp in seconds
            beats: List of beat timestamps
            tolerance: Allowed deviation in seconds (default 150ms)

        Returns:
            True if on beat, False otherwise
        """
        _, diff = self.find_closest_beat(timestamp, beats)
        return diff <= tolerance

    def calculate_rhythm_accuracy(
        self,
        step_times: List[float],
        beats: List[float],
        tolerance: float = 0.15
    ) -> Dict[str, Any]:
        """
        Calculate how well steps match beats.

        Args:
            step_times: List of step timestamps
            beats: List of beat timestamps
            tolerance: Allowed deviation for "on beat" classification

        Returns:
            Dict with accuracy, on_beat_count, off_beat steps
        """
        if not step_times:
            return {"accuracy": 0.0, "on_beat": 0, "total": 0, "off_beat_steps": []}

        on_beat = 0
        off_beat_steps = []

        for step_time in step_times:
            _, diff = self.find_closest_beat(step_time, beats)
            if diff <= tolerance:
                on_beat += 1
            else:
                off_beat_steps.append({
                    "timestamp": round(step_time, 3),
                    "deviation": round(diff, 3)
                })

        total = len(step_times)
        return {
            "accuracy": round(on_beat / total * 100, 1) if total > 0 else 0.0,
            "on_beat": on_beat,
            "total": total,
            "off_beat_steps": off_beat_steps
        }


# Singleton instance
audio_service = AudioService()
