"""
Manual check for screenshot rendering.

Renders one error screenshot from a given video and timestamp, and prints
how long it took. Used to verify Cyrillic captions and timing.

Usage:
    python scripts/test_visualization.py <video_path> [timestamp]
"""

import sys
import time
from pathlib import Path

# Allow running as a plain script from the backend directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.visualization_service import visualization_service  # noqa: E402


def main() -> None:
    """Render one screenshot and report timing."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_visualization.py <video_path> [timestamp]")
        raise SystemExit(1)

    video_path = sys.argv[1]
    timestamp = float(sys.argv[2]) if len(sys.argv) > 2 else 10.855

    started = time.time()
    path = visualization_service.create_error_screenshot(
        video_path,
        timestamp,
        {
            "title": "Шаг не в бит",
            "recommendation": (
                "Слушайте бит музыки и старайтесь попадать шагом точно в удар"
            ),
            "analysis_id": 999,
            "error_id": 1,
        },
        detected_element=None,
    )
    elapsed = time.time() - started

    import cv2
    image = cv2.imread(path)
    shape = image.shape if image is not None else None

    print(f"rendered in {elapsed:.2f}s -> {path}")
    print(f"image shape: {shape}")


if __name__ == "__main__":
    main()
