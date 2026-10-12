"""
Video utilities for processing dance videos.

Provides FFmpeg wrappers for audio extraction, video info, and frame extraction.
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional


def get_video_info(video_path: str) -> Dict[str, Any]:
    """
    Get video metadata using ffprobe.

    Args:
        video_path: Path to video file

    Returns:
        Dict with duration, fps, width, height, codec info

    Raises:
        RuntimeError: If ffprobe fails or video is invalid
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                video_path
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")

        data = json.loads(result.stdout)

        # Find video stream
        video_stream = None
        audio_stream = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video" and video_stream is None:
                video_stream = stream
            elif stream.get("codec_type") == "audio" and audio_stream is None:
                audio_stream = stream

        if not video_stream:
            raise RuntimeError("No video stream found")

        # Parse FPS
        fps = 30.0
        fps_str = video_stream.get("r_frame_rate", "30/1")
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 30.0

        format_info = data.get("format", {})

        return {
            "duration": float(format_info.get("duration", 0)),
            "size": int(format_info.get("size", 0)),
            "format": format_info.get("format_name", "unknown"),
            "fps": fps,
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "codec": video_stream.get("codec_name", "unknown"),
            "has_audio": audio_stream is not None,
            "audio_codec": audio_stream.get("codec_name") if audio_stream else None
        }

    except subprocess.TimeoutExpired:
        raise RuntimeError("ffprobe timed out")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse ffprobe output: {e}")


def extract_audio(video_path: str, output_path: str, sample_rate: int = 22050) -> str:
    """
    Extract audio track from video using FFmpeg.

    Args:
        video_path: Path to video file
        output_path: Path for output WAV file
        sample_rate: Audio sample rate (default 22050 for librosa)

    Returns:
        Path to extracted audio file

    Raises:
        RuntimeError: If extraction fails or video has no audio
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",  # Overwrite output
            "-i", video_path,
            "-vn",  # No video
            "-acodec", "pcm_s16le",
            "-ar", str(sample_rate),
            "-ac", "1",  # Mono
            str(output)
        ],
        capture_output=True,
        text=True,
        timeout=300
    )

    if result.returncode != 0:
        raise RuntimeError(f"Audio extraction failed: {result.stderr}")

    if not output.exists():
        raise RuntimeError("Audio file was not created")

    return str(output)


def extract_frame(video_path: str, timestamp: float, output_path: str) -> str:
    """
    Extract single frame from video at given timestamp.

    Args:
        video_path: Path to video file
        timestamp: Timestamp in seconds
        output_path: Path for output image file

    Returns:
        Path to extracted frame

    Raises:
        RuntimeError: If extraction fails
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss", str(timestamp),
            "-i", video_path,
            "-frames:v", "1",
            "-q:v", "2",  # High quality
            str(output)
        ],
        capture_output=True,
        text=True,
        timeout=60
    )

    if result.returncode != 0:
        raise RuntimeError(f"Frame extraction failed: {result.stderr}")

    if not output.exists():
        raise RuntimeError("Frame image was not created")

    return str(output)


def extract_frames_batch(
    video_path: str,
    timestamps: list[float],
    output_dir: str,
    prefix: str = "frame"
) -> list[str]:
    """
    Extract multiple frames from video at given timestamps.

    Args:
        video_path: Path to video file
        timestamps: List of timestamps in seconds
        output_dir: Directory for output images
        prefix: Filename prefix

    Returns:
        List of paths to extracted frames
    """
    output_paths = []
    for i, ts in enumerate(timestamps):
        output_path = str(Path(output_dir) / f"{prefix}_{i:04d}_{ts:.2f}s.jpg")
        output_paths.append(extract_frame(video_path, ts, output_path))
    return output_paths


def validate_video(video_path: str, max_duration: int = 600) -> Dict[str, Any]:
    """
    Validate video file for processing.

    Checks: file exists, is valid video, duration within limits.

    Args:
        video_path: Path to video file
        max_duration: Maximum allowed duration in seconds

    Returns:
        Dict with validation result and video info

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If video is invalid or too long
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    info = get_video_info(video_path)

    if info["duration"] <= 0:
        raise ValueError("Invalid video: duration is zero")

    if info["duration"] > max_duration:
        raise ValueError(
            f"Video too long: {info['duration']:.1f}s (max {max_duration}s)"
        )

    return {"valid": True, "info": info}
