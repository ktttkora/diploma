"""
Script to extract pose landmarks from reference dance videos.

Processes all videos in the dataset directory and saves pose data as JSON files.
Supports resume - skips already processed videos.
"""

import os
import sys
import cv2
import json
import argparse
import mediapipe as mp
from pathlib import Path
from tqdm import tqdm
from datetime import datetime
from typing import Dict, List, Optional, Any


DATASET_PATH = "C:/Users/kt/important/university/diploma/hasl_files"
# Output path resolved relative to this script's location: backend/data/reference_poses
OUTPUT_PATH = str(Path(__file__).resolve().parent.parent / "data" / "reference_poses")

mp_pose = mp.solutions.pose


def extract_element_name(filename: str) -> str:
    """Extract element name from video filename."""
    return Path(filename).stem


def process_video(video_path: str, element_name: str) -> Dict[str, Any]:
    """
    Process video and extract pose landmarks using MediaPipe.

    Args:
        video_path: Path to video file
        element_name: Name of dance element

    Returns:
        Dictionary with element metadata and pose landmarks

    Raises:
        RuntimeError: If video cannot be opened or processed
    """
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as pose:
        poses: List[Dict[str, Any]] = []
        frame_count = 0
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = pose.process(frame_rgb)

            if result.pose_landmarks:
                landmarks = [
                    {
                        "x": float(lm.x),
                        "y": float(lm.y),
                        "z": float(lm.z),
                        "visibility": float(lm.visibility)
                    }
                    for lm in result.pose_landmarks.landmark
                ]

                poses.append({
                    "frame": frame_count,
                    "timestamp": round(frame_count / fps, 3),
                    "landmarks": landmarks
                })

            frame_count += 1

        cap.release()

    if frame_count == 0:
        raise RuntimeError("No frames extracted from video")

    return {
        "element": element_name,
        "total_frames": frame_count,
        "fps": fps,
        "duration": round(frame_count / fps, 2),
        "poses_count": len(poses),
        "poses": poses,
        "processed_at": datetime.now().isoformat()
    }


def save_reference(data: Dict[str, Any], element_name: str) -> None:
    """
    Save reference pose data to JSON file.

    Args:
        data: Pose data dictionary
        element_name: Name for output file
    """
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    output_file = os.path.join(OUTPUT_PATH, f"{element_name}.json")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    """Main processing loop."""
    parser = argparse.ArgumentParser(description="Extract pose landmarks from reference videos")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--limit", type=int, default=None, help="Process only first N videos")
    args = parser.parse_args()

    print("=" * 60)
    print("🎬 ОБРАБОТКА ДАТАСЕТА ЭТАЛОННЫХ ВИДЕО")
    print("=" * 60)
    print(f"📁 Датасет: {DATASET_PATH}")
    print(f"💾 Результат: {OUTPUT_PATH}")
    print()

    if not os.path.exists(DATASET_PATH):
        print(f"❌ Датасет не найден: {DATASET_PATH}")
        return

    video_files = [
        f for f in os.listdir(DATASET_PATH)
        if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))
    ]

    if not video_files:
        print("❌ Видео не найдены")
        return

    if args.limit:
        video_files = video_files[:args.limit]

    print(f"📊 Найдено видео: {len(video_files)}")
    print(f"⏱️  Время: CPU ~5-7 часов, GPU ~1-2 часа")
    print()

    if not args.yes:
        input("Нажмите Enter для начала...")
    print()

    start_time = datetime.now()
    success_count = 0
    error_count = 0

    for video_file in tqdm(video_files, desc="🎬 Обработка", unit="видео"):
        element_name = extract_element_name(video_file)
        video_path = os.path.join(DATASET_PATH, video_file)

        # Skip already processed
        output_file = os.path.join(OUTPUT_PATH, f"{element_name}.json")
        if os.path.exists(output_file):
            tqdm.write(f"⏭️  {element_name}: уже обработан")
            success_count += 1
            continue

        try:
            data = process_video(video_path, element_name)
            save_reference(data, element_name)

            tqdm.write(
                f"✅ {element_name}: "
                f"{data['poses_count']} поз из {data['total_frames']} кадров"
            )
            success_count += 1

        except Exception as e:
            tqdm.write(f"❌ {video_file}: {e}")
            error_count += 1

            # Log error to file
            with open("errors.log", "a", encoding="utf-8") as log:
                log.write(f"{datetime.now().isoformat()} | {video_file} | {e}\n")

    duration = datetime.now() - start_time

    print()
    print("=" * 60)
    print("🎉 ОБРАБОТКА ЗАВЕРШЕНА!")
    print("=" * 60)
    print(f"✅ Успешно: {success_count}")
    print(f"❌ Ошибок: {error_count}")
    print(f"⏱️  Время: {duration}")
    print(f"💾 Сохранено в: {OUTPUT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
