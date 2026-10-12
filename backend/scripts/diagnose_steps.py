"""
Diagnostic for step detection on real footage.

Prints the ankle vertical signal and the detected step positions so the
detector's behaviour can be judged against the actual motion.

Usage:
    python scripts/diagnose_steps.py <video_path>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.pose_service import pose_service  # noqa: E402


def main() -> None:
    """Print an ASCII trace of ankle motion with detected steps marked."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/diagnose_steps.py <video_path>")
        raise SystemExit(1)

    video_path = sys.argv[1]

    poses = pose_service.extract_poses_from_video(video_path)
    detected = [p for p in poses if p.get("detected")]
    print(f"frames: {len(poses)}, with pose: {len(detected)}")

    if not detected:
        print("no poses detected")
        return

    steps = pose_service.detect_steps(poses)
    step_times = {round(s["timestamp"], 2) for s in steps}
    print(f"steps detected: {len(steps)}")
    print()

    # Sample the left ankle at ~2 Hz and draw the trace
    series = []
    for pose in detected:
        series.append((pose["timestamp"], pose["landmarks"][27]["y"]))

    lo = min(y for _, y in series)
    hi = max(y for _, y in series)
    span = hi - lo or 1.0
    print(f"left ankle y range: {lo:.3f} .. {hi:.3f} (span {span:.3f})")
    print()

    width = 60
    print(f"{'time':>7}  {'y':>6}  trace")
    for timestamp, y in series:
        if round(timestamp, 2) not in step_times:
            continue
        position = int((y - lo) / span * (width - 1))
        bar = " " * position + "*"
        print(f"{timestamp:7.2f}  {y:6.3f}  |{bar}")
    print()
    print("(* = detected step; y grows downwards, so a taller bar means a lower foot)")


if __name__ == "__main__":
    main()
