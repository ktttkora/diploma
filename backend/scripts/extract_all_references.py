"""
Script to extract pose landmarks from reference dance videos.

Processes all videos in the dataset directory in parallel and saves pose data
as compact JSON files. Supports resume - skips already processed videos.
JSON files are written atomically (tmp file + os.replace), so an interrupted
run never leaves a truncated JSON that resume would treat as done.
"""

import argparse
import json
import math
import os
import signal
import sys
from concurrent.futures import FIRST_COMPLETED, Future, ProcessPoolExecutor, wait
from concurrent.futures.process import BrokenProcessPool
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Set, Tuple

import cv2
import mediapipe as mp
from tqdm import tqdm


# Paths resolved relative to this script's location (backend/scripts)
BACKEND_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = str(Path(__file__).resolve().parents[2] / "hasl_files")
OUTPUT_PATH = str(BACKEND_DIR / "data" / "reference_poses")
ERRORS_LOG_PATH = str(BACKEND_DIR / "data" / "extract_errors.log")

VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv')
# Preferred extension when several files share one element name
EXTENSION_PRIORITY = {'.mp4': 0, '.mov': 1}
COORD_PRECISION = 5
DEFAULT_FPS = 30.0
MAX_FPS = 240.0
FRAME_COUNT_TOLERANCE = 0.05
MAX_TASKS_PER_CHILD = 20
POLL_INTERVAL = 0.5

mp_pose = mp.solutions.pose


def extract_element_name(filename: str) -> str:
    """
    Extract element name from video filename.

    Args:
        filename: Video filename

    Returns:
        Filename without extension
    """
    return Path(filename).stem


def safe_int(value: float) -> int:
    """
    Convert an OpenCV property value to int, mapping NaN/inf/negative to 0.

    Args:
        value: Raw property value

    Returns:
        Non-negative integer
    """
    if not math.isfinite(value) or value <= 0:
        return 0
    return int(value)


def init_worker() -> None:
    """
    Pool worker initializer.

    Workers ignore Ctrl+C / Ctrl+Break so only the main process handles
    interruption. OpenCV is limited to one thread per process to avoid
    CPU oversubscription with many workers.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, signal.SIG_IGN)
    cv2.setNumThreads(1)


def process_video(video_path: str, element_name: str) -> Dict[str, Any]:
    """
    Process video and extract pose landmarks using MediaPipe.

    Args:
        video_path: Path to video file
        element_name: Name of dance element

    Returns:
        Dictionary with element metadata and pose landmarks, plus a
        "_warnings" list that must be removed before saving

    Raises:
        RuntimeError: If video cannot be opened or processed
    """
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    warnings: List[str] = []
    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        if not math.isfinite(fps) or fps <= 0 or fps > MAX_FPS:
            fps = DEFAULT_FPS
        expected_frames = float(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = safe_int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = safe_int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        with mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        ) as pose:
            poses: List[Dict[str, Any]] = []
            frame_count = 0

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                # Landmarks are normalized to the decoded frame, so its shape
                # wins over container metadata (which may be 0 or ignore rotation)
                if frame_count == 0:
                    frame_h, frame_w = int(frame.shape[0]), int(frame.shape[1])
                    if (frame_w, frame_h) != (width, height):
                        if width > 0 and height > 0:
                            warnings.append(
                                f"WARNING container size {width}x{height} differs from "
                                f"decoded frame {frame_w}x{frame_h}, using frame size"
                            )
                        width, height = frame_w, frame_h

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = pose.process(frame_rgb)

                if result.pose_landmarks:
                    landmarks = [
                        {
                            "x": round(float(lm.x), COORD_PRECISION),
                            "y": round(float(lm.y), COORD_PRECISION),
                            "z": round(float(lm.z), COORD_PRECISION),
                            "visibility": round(float(lm.visibility), COORD_PRECISION)
                        }
                        for lm in result.pose_landmarks.landmark
                    ]

                    poses.append({
                        "frame": frame_count,
                        "timestamp": round(frame_count / fps, 3),
                        "landmarks": landmarks
                    })

                frame_count += 1
    finally:
        cap.release()

    if frame_count == 0:
        raise RuntimeError("No frames extracted from video")

    if math.isfinite(expected_frames) and expected_frames > 0:
        diff = abs(frame_count - expected_frames) / expected_frames
        if diff > FRAME_COUNT_TOLERANCE:
            warnings.append(
                f"WARNING frame count mismatch: read {frame_count}, "
                f"container reports {int(expected_frames)} ({diff:.1%})"
            )
    if not poses:
        warnings.append(f"WARNING no poses detected in {frame_count} frames")

    return {
        "element": element_name,
        "total_frames": frame_count,
        "fps": fps,
        "width": width,
        "height": height,
        "duration": round(frame_count / fps, 2),
        "poses_count": len(poses),
        "poses": poses,
        "processed_at": datetime.now().isoformat(),
        "_warnings": warnings,
    }


def save_reference(data: Dict[str, Any], element_name: str, output_path: str = OUTPUT_PATH) -> str:
    """
    Save reference pose data to JSON file atomically.

    Writes to <name>.json.tmp first, then renames via os.replace.

    Args:
        data: Pose data dictionary
        element_name: Name for output file
        output_path: Output directory

    Returns:
        Path to the saved JSON file
    """
    os.makedirs(output_path, exist_ok=True)
    output_file = os.path.join(output_path, f"{element_name}.json")
    tmp_file = f"{output_file}.tmp"

    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    os.replace(tmp_file, output_file)
    return output_file


def process_and_save(video_path: str, element_name: str, output_path: str) -> Dict[str, Any]:
    """
    Worker entry point: process one video and save its JSON.

    Only a short summary is returned to the main process to avoid
    pickling megabytes of landmarks.

    Args:
        video_path: Path to video file
        element_name: Name of dance element
        output_path: Output directory

    Returns:
        Summary dict: name, file, poses_count, total_frames, seconds,
        warnings, or error
    """
    started = datetime.now()
    try:
        data = process_video(video_path, element_name)
        # Warnings go to the main process log, not into the JSON
        warnings = data.pop("_warnings", [])
        save_reference(data, element_name, output_path)
        return {
            "name": element_name,
            "file": os.path.basename(video_path),
            "poses_count": data["poses_count"],
            "total_frames": data["total_frames"],
            "seconds": (datetime.now() - started).total_seconds(),
            "warnings": warnings,
            "error": None,
        }
    except Exception as e:
        return {
            "name": element_name,
            "file": os.path.basename(video_path),
            "seconds": (datetime.now() - started).total_seconds(),
            "warnings": [],
            "error": f"{type(e).__name__}: {e}",
        }


def collect_videos(dataset_path: str) -> Tuple[List[str], List[str]]:
    """
    Collect video files with unique element names.

    Names are compared case-insensitively because NTFS is case-insensitive.
    For duplicates, .mp4 is preferred over .mov, then other extensions.

    Args:
        dataset_path: Dataset directory

    Returns:
        Tuple of (video filenames, skipped duplicate filenames)
    """
    files = sorted(
        f for f in os.listdir(dataset_path)
        if f.lower().endswith(VIDEO_EXTENSIONS)
    )
    groups: Dict[str, List[str]] = {}
    for f in files:
        groups.setdefault(extract_element_name(f).casefold(), []).append(f)

    unique: List[str] = []
    duplicates: List[str] = []
    for f in files:
        group = groups[extract_element_name(f).casefold()]
        # Within a duplicate group prefer .mp4, then .mov, then the rest
        best = min(group, key=lambda g: (EXTENSION_PRIORITY.get(Path(g).suffix.lower(), 99), g))
        if f == best:
            unique.append(f)
        else:
            duplicates.append(f)
    return unique, duplicates


def log_error(log_path: str, video_file: str, error: str) -> None:
    """
    Append an error or warning line to the errors log.

    Args:
        log_path: Path to the log file
        video_file: Video filename the message refers to
        error: Message text
    """
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(f"{datetime.now().isoformat()} | {video_file} | {error}\n")


def terminate_workers(executor: ProcessPoolExecutor) -> None:
    """
    Cancel pending tasks and kill worker processes still running.

    Args:
        executor: Process pool to stop
    """
    # Private attribute, but the only way to stop videos already in progress.
    # Must be read before shutdown(), which resets it to None.
    processes = list((getattr(executor, "_processes", None) or {}).values())
    executor.shutdown(wait=False, cancel_futures=True)
    for proc in processes:
        try:
            proc.terminate()
        except Exception:
            pass
    for proc in processes:
        try:
            proc.join(timeout=5)
        except Exception:
            pass


def iter_completed(futures: Dict[Future, str]) -> Iterator[Future]:
    """
    Yield futures as they complete, staying responsive to Ctrl+C.

    concurrent.futures.as_completed() without a timeout blocks on a lock
    that Ctrl+C cannot interrupt on Windows, so poll with a short timeout.

    Args:
        futures: Futures to wait for

    Yields:
        Completed futures
    """
    not_done: Set[Future] = set(futures)
    while not_done:
        done, not_done = wait(not_done, timeout=POLL_INTERVAL, return_when=FIRST_COMPLETED)
        yield from done


def raise_keyboard_interrupt(signum: int, frame: Any) -> None:
    """
    Signal handler that turns Ctrl+Break into KeyboardInterrupt.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    raise KeyboardInterrupt


def main() -> None:
    """
    Main processing loop.

    Parses CLI arguments, collects videos, skips already processed ones and
    processes the rest in a process pool.

    Returns:
        None. Exits with code 130 on Ctrl+C / Ctrl+Break.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Extract pose landmarks from reference videos")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--limit", type=int, default=None, help="Process only first N videos")
    parser.add_argument("--dataset", default=DATASET_PATH, help="Dataset directory with videos")
    parser.add_argument("--output", default=OUTPUT_PATH, help="Output directory for JSON files")
    parser.add_argument(
        "--workers", type=int, default=max(1, (os.cpu_count() or 1) - 2),
        help="Number of parallel worker processes"
    )
    args = parser.parse_args()

    dataset_path: str = args.dataset
    output_path: str = args.output
    workers: int = max(1, args.workers)
    # Errors log lives next to the output directory
    errors_log = (
        ERRORS_LOG_PATH if os.path.abspath(output_path) == os.path.abspath(OUTPUT_PATH)
        else os.path.join(os.path.dirname(os.path.abspath(output_path)), "extract_errors.log")
    )

    print("=" * 60)
    print("🎬 ОБРАБОТКА ДАТАСЕТА ЭТАЛОННЫХ ВИДЕО")
    print("=" * 60)
    print(f"📁 Датасет: {dataset_path}")
    print(f"💾 Результат: {output_path}")
    print(f"🧵 Процессов: {workers}")
    print()

    if not os.path.exists(dataset_path):
        print(f"❌ Датасет не найден: {dataset_path}")
        return

    video_files, duplicates = collect_videos(dataset_path)

    if not video_files:
        print("❌ Видео не найдены")
        return

    for dup in duplicates:
        print(f"⚠️  Дубликат имени элемента, пропущен: {dup}")
        log_error(errors_log, dup, "WARNING duplicate element name, skipped")

    if args.limit:
        video_files = video_files[:args.limit]

    # Resume: skip already processed before submitting to the pool
    pending: List[str] = []
    skipped = 0
    for video_file in video_files:
        output_file = os.path.join(output_path, f"{extract_element_name(video_file)}.json")
        if os.path.exists(output_file):
            skipped += 1
        else:
            pending.append(video_file)

    print(f"📊 Найдено видео: {len(video_files)}")
    print(f"⏭️  Уже обработано: {skipped}")
    print(f"▶️  К обработке: {len(pending)}")
    print()

    if not pending:
        print("✅ Всё уже обработано")
        return

    if not args.yes:
        input("Нажмите Enter для начала...")
    print()

    os.makedirs(output_path, exist_ok=True)
    start_time = datetime.now()
    success_count = 0
    error_count = 0

    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, raise_keyboard_interrupt)

    executor = ProcessPoolExecutor(
        max_workers=workers,
        initializer=init_worker,
        max_tasks_per_child=MAX_TASKS_PER_CHILD,
    )
    interrupted = False
    try:
        futures: Dict[Future, str] = {
            executor.submit(
                process_and_save,
                os.path.join(dataset_path, video_file),
                extract_element_name(video_file),
                output_path,
            ): video_file
            for video_file in pending
        }
        progress = tqdm(total=len(futures), desc="🎬 Обработка", unit="видео")
        for future in iter_completed(futures):
            progress.update(1)
            video_file = futures[future]
            try:
                summary = future.result()
            except BrokenProcessPool as e:
                error_count += 1
                log_error(errors_log, video_file, f"BrokenProcessPool: {e}")
                tqdm.write(f"❌ {video_file}: пул процессов упал")
                tqdm.write("💥 Пул упал, перезапустите скрипт (resume продолжит с места остановки)")
                break
            except Exception as e:
                summary = {
                    "name": extract_element_name(video_file),
                    "file": video_file,
                    "seconds": 0.0,
                    "warnings": [],
                    "error": f"{type(e).__name__}: {e}",
                }

            for warning in summary.get("warnings", []):
                tqdm.write(f"⚠️  {summary['file']}: {warning}")
                log_error(errors_log, summary["file"], warning)

            if summary["error"] is None:
                success_count += 1
                tqdm.write(
                    f"✅ {summary['name']}: "
                    f"{summary['poses_count']} поз из {summary['total_frames']} кадров "
                    f"({summary['seconds']:.1f} с)"
                )
            else:
                error_count += 1
                tqdm.write(f"❌ {summary['file']}: {summary['error']}")
                log_error(errors_log, summary["file"], summary["error"])
        progress.close()
    except KeyboardInterrupt:
        interrupted = True
        terminate_workers(executor)
        print()
        print("⛔ Прервано, перезапустите скрипт для продолжения (resume пропустит готовые)")
        print(f"✅ Успешно до прерывания: {success_count}, ❌ ошибок: {error_count}")
        sys.exit(130)
    finally:
        if not interrupted:
            executor.shutdown(wait=True, cancel_futures=True)

    duration = datetime.now() - start_time

    print()
    print("=" * 60)
    print("🎉 ОБРАБОТКА ЗАВЕРШЕНА!")
    print("=" * 60)
    print(f"✅ Успешно: {success_count}")
    print(f"⏭️  Пропущено (уже было): {skipped}")
    print(f"❌ Ошибок: {error_count}")
    if error_count:
        print(f"📝 Лог ошибок: {errors_log}")
    print(f"⏱️  Время: {duration}")
    print(f"💾 Сохранено в: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
