"""
Build or refresh the compact reference pose index offline.

Run after generating reference JSONs, so the first analysis does not pay
for reading every reference file:

    cd backend
    venv\\Scripts\\python.exe scripts\\build_reference_index.py

Only new or modified reference files are re-read; progress is saved every
--save-every elements, so the script can be interrupted and re-run.
"""

import argparse
import logging
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.reference_service import INDEX_SAVE_EVERY, build_reference_index  # noqa: E402


def main() -> int:
    """
    Parse arguments and build the index.

    Returns:
        Process exit code
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description="Build the reference pose similarity index")
    parser.add_argument(
        "--reference-dir", default=str(BACKEND_DIR / "data" / "reference_poses"),
        help="Directory with reference JSON files"
    )
    parser.add_argument(
        "--index-path", default=None,
        help="Index file (default: settings.REFERENCE_INDEX_PATH)"
    )
    parser.add_argument(
        "--videos-dir", default=None,
        help="Source videos, used when a JSON has no width/height "
             "(default: settings.REFERENCE_VIDEOS_FOLDER)"
    )
    parser.add_argument(
        "--save-every", type=int, default=INDEX_SAVE_EVERY,
        help="Save the index after this many refreshed elements"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    started = time.monotonic()

    def progress(done: int, total: int, stem: str) -> None:
        if done == total or done % 25 == 0:
            print(f"[{done}/{total}] {stem}", flush=True)

    stats = build_reference_index(
        reference_dir=args.reference_dir,
        index_path=args.index_path,
        videos_dir=args.videos_dir,
        save_every=args.save_every,
        progress=progress,
    )

    print(
        f"Done in {time.monotonic() - started:.1f}s: total={stats['total']} "
        f"refreshed={stats['refreshed']} removed={stats['removed']} "
        f"failed={stats['failed']} index={stats['index_path']}"
    )
    return 1 if stats["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
