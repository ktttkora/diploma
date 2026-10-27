"""
Key frame extraction utilities.

Selects representative frames from a video for AI analysis:
evenly-spaced sampling plus frames near detected motion peaks.
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.utils.video_utils import extract_frame, extract_frames_batch, get_video_info


def calculate_key_timestamps(
    duration: float,
    count: int = 20,
    start_ratio: float = 0.05,
    end_ratio: float = 0.95
) -> List[float]:
    """
    Calculate evenly-spaced timestamps, skipping the very start and end.

    The first and last moments of a clip are usually a standing pose rather
    than dancing, so they are skipped by default.

    Args:
        duration: Video duration in seconds
        count: How many timestamps to produce
        start_ratio: Where sampling starts (fraction of duration)
        end_ratio: Where sampling ends (fraction of duration)

    Returns:
        Sorted list of timestamps in seconds

    Raises:
        ValueError: If duration is not positive or count is not positive
    """
    if duration <= 0:
        raise ValueError("duration must be positive")
    if count <= 0:
        raise ValueError("count must be positive")

    start = duration * start_ratio
    end = duration * end_ratio
    span = end - start

    if span <= 0:
        return [round(duration / 2, 3)]

    step = span / count
    return [round(start + step * (i + 0.5), 3) for i in range(count)]


def extract_key_frames(
    video_path: str,
    output_dir: str,
    count: int = 20,
    max_width: int = 720
) -> List[str]:
    """
    Extract representative frames from a video for AI analysis.

    Frames are downscaled to keep the API payload small (large frames add
    cost and latency without improving pose recognition).

    Args:
        video_path: Path to video file
        output_dir: Directory to write JPEG frames into
        count: Number of frames to extract
        max_width: Downscale frames wider than this (0 disables)

    Returns:
        List of paths to extracted frames, in chronological order

    Raises:
        RuntimeError: If the video has no readable duration or frame extraction fails
    """
    info = get_video_info(video_path)
    duration = info.get("duration", 0)
    if duration <= 0:
        raise RuntimeError("Cannot determine video duration")

    timestamps = calculate_key_timestamps(duration, count=count)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    frame_paths = extract_frames_batch(
        video_path,
        timestamps,
        str(output_path),
        prefix="key"
    )

    if max_width and info.get("width", 0) > max_width:
        for path in frame_paths:
            downscale_frame(path, max_width)

    return frame_paths


# Matches the "<prefix>_<index>_<seconds>s.<ext>" names of extract_frames_batch
_FRAME_TIMESTAMP_RE = re.compile(r"_(\d+(?:\.\d+)?)s\.(?:jpe?g|png)$", re.IGNORECASE)


def parse_frame_timestamp(frame_path: str) -> Optional[float]:
    """
    Read the video timestamp encoded in a key frame file name.

    Args:
        frame_path: Path produced by extract_key_frames / extract_frames_batch

    Returns:
        Timestamp in seconds, or None if the name carries no timestamp
    """
    match = _FRAME_TIMESTAMP_RE.search(Path(frame_path).name)
    return float(match.group(1)) if match else None


def downscale_frame(frame_path: str, max_width: int) -> None:
    """
    Downscale an image in place if it is wider than max_width.

    Args:
        frame_path: Path to image file
        max_width: Target maximum width in pixels
    """
    import cv2

    image = cv2.imread(frame_path)
    if image is None:
        return

    height, width = image.shape[:2]
    if width <= max_width:
        return

    scale = max_width / width
    resized = cv2.resize(
        image,
        (max_width, int(height * scale)),
        interpolation=cv2.INTER_AREA
    )
    cv2.imwrite(frame_path, resized)


def extract_frames_for_errors(
    video_path: str,
    timestamps: List[float],
    output_dir: str
) -> Dict[float, str]:
    """
    Extract one frame per error timestamp (for screenshots).

    Args:
        video_path: Path to video file
        timestamps: Error timestamps in seconds
        output_dir: Directory to write frames into

    Returns:
        Mapping of timestamp -> frame path (only for frames written successfully)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    frames: Dict[float, str] = {}
    for timestamp in timestamps:
        frame_path = str(output_path / f"error_{timestamp:.2f}s.jpg")
        try:
            extract_frame(video_path, timestamp, frame_path)
            frames[timestamp] = frame_path
        except RuntimeError:
            continue

    return frames
