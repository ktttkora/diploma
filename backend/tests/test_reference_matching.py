"""
Unit tests for reference element catalog, similarity index, candidate
selection and example frame extraction.

All references are synthetic and live in tmp_path.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np
import pytest

from app.services.reference_service import (
    ReferenceService,
    normalize_element_name,
    normalize_pose,
    mirror_poses,
    INDEX_SAMPLES_PER_ELEMENT,
)


def make_landmarks(arm_raise: float, lean: float = 0.0, shift: float = 0.0,
                   scale: float = 1.0) -> List[Dict[str, float]]:
    """
    Build 33 synthetic MediaPipe landmarks.

    Args:
        arm_raise: Wrist height relative to shoulders (positive = up)
        lean: Horizontal offset of the right wrist (breaks left/right symmetry)
        shift: Horizontal shift of the whole body
        scale: Body size factor
    """
    points = {i: (0.5, 0.5) for i in range(33)}
    body: Dict[int, Tuple[float, float]] = {
        11: (-0.1, -0.3), 12: (0.1, -0.3),            # shoulders
        13: (-0.15, -0.3 - arm_raise / 2), 14: (0.15, -0.3 - arm_raise / 2),
        15: (-0.2, -0.3 - arm_raise), 16: (0.2 + lean, -0.3 - arm_raise),
        23: (-0.07, 0.0), 24: (0.07, 0.0),            # hips
        25: (-0.08, 0.2), 26: (0.08, 0.2),
        27: (-0.08, 0.4), 28: (0.08, 0.4),
    }
    for idx, (x, y) in body.items():
        points[idx] = (0.5 + shift + x * scale, 0.5 + y * scale)
    return [{"x": x, "y": y, "z": 0.0, "visibility": 0.99} for x, y in
            (points[i] for i in range(33))]


def write_reference(directory: Path, name: str, arm_raise: float,
                    frames: int = 40, lean: float = 0.0) -> Path:
    """Write a synthetic reference JSON in the real dataset format."""
    poses = [
        {"frame": i, "timestamp": round(i / 30.0, 3),
         "landmarks": make_landmarks(arm_raise + 0.01 * np.sin(i), lean=lean)}
        for i in range(frames)
    ]
    data = {
        "element": name, "total_frames": frames, "fps": 30.0,
        "duration": frames / 30.0, "poses_count": frames, "poses": poses,
        "processed_at": "2026-10-24T00:00:00",
    }
    path = directory / f"{name}.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def user_poses(arm_raise: float, count: int = 50, lean: float = 0.0,
               shift: float = 0.2, scale: float = 0.6) -> List[Dict]:
    """User poses as returned by PoseService (shifted and scaled)."""
    poses = [
        {"frame": i, "timestamp": i / 30.0, "detected": True,
         "landmarks": make_landmarks(arm_raise, lean=lean, shift=shift, scale=scale)}
        for i in range(count)
    ]
    poses.append({"frame": count, "timestamp": count / 30.0,
                  "detected": False, "landmarks": []})
    return poses


@pytest.fixture
def ref_env(tmp_path: Path) -> Dict[str, Path]:
    """Directories for references, videos, frames and the index."""
    dirs = {
        "refs": tmp_path / "reference_poses",
        "videos": tmp_path / "videos",
        "frames": tmp_path / "reference_frames",
        "index": tmp_path / "reference_index.json",
    }
    dirs["refs"].mkdir()
    dirs["videos"].mkdir()
    return dirs


def make_service(env: Dict[str, Path]) -> ReferenceService:
    return ReferenceService(
        str(env["refs"]), videos_dir=str(env["videos"]),
        frames_dir=str(env["frames"]), index_path=str(env["index"]),
    )


# ----------------------------------------------------------------------
# Names
# ----------------------------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("_Старт. Американка-Свивлы", "Старт. Американка-Свивлы"),
    ("!_Партнерша_Свитч2", "Партнерша Свитч"),
    ("Свивлы (Американка)-1", "Свивлы (Американка)"),
    ("Верхний Спин - Харлей #2", "Верхний Спин - Харлей"),
    ("Раскрытие с закрытием с приседанием_v2", "Раскрытие с закрытием с приседанием"),
    ("Раскрытие-Кошечка-Свитч 2", "Раскрытие-Кошечка-Свитч"),
    ("Солнышко", "Солнышко"),
    ("Катапульта. Свителев", "Катапульта"),
    ("Препы-Выпад. Свителев-2", "Препы-Выпад"),
    ("БэкСпин 2 руки - Корзинка - Свитч (Тагиров)", "БэкСпин 2 руки - Корзинка - Свитч"),
    ("Харлей. Подробно", "Харлей"),
    ("РолИн-РолАут_ПОДРОБНО", "РолИн-РолАут"),
    ("_Старт. Крабики (Фаст) (1)", "Старт. Крабики (Фаст)"),
    ("Корзинка-Пируэт(М) [3 варианта]", "Корзинка-Пируэт(М)"),
    ("_Старт. Радуга. Твист. 2 варианта", "Старт. Радуга. Твист"),
    ("Йо-Йо_Макарчук", "Йо-Йо"),
    ("Бампер. Руки назад", "Бампер. Руки назад"),
    ("Поддержка (локоть2)", "Поддержка (локоть2)"),
])
def test_normalize_element_name(raw: str, expected: str) -> None:
    """Prefixes, variants, authors and descriptive tails are cleaned up."""
    assert normalize_element_name(raw) == expected


def test_catalog_merges_case_variants(ref_env) -> None:
    """Names differing only in case/author map to one display and one file."""
    for name in ["_Старт. Крабики (Фаст) (1)", "_Старт. Крабики (фаст)",
                 "Катапульта", "Катапульта. Свителев", "Катапульта. Подробно"]:
        write_reference(ref_env["refs"], name, 0.2)
    catalog = make_service(ref_env).get_element_catalog()

    assert catalog == {
        "Катапульта": "Катапульта",
        "Старт. Крабики (фаст)": "_Старт. Крабики (фаст)",
    }


def test_catalog_deduplicates_variants(ref_env) -> None:
    """Variants collapse into one display name pointing at a real stem."""
    for name in ["!_Партнерша_Свитч", "!_Партнерша_Свитч2", "Солнышко", "_Старт Солнышко"]:
        write_reference(ref_env["refs"], name, 0.2)
    catalog = make_service(ref_env).get_element_catalog()

    assert catalog["Партнерша Свитч"] == "!_Партнерша_Свитч"
    assert catalog["Солнышко"] == "Солнышко"
    assert catalog["Старт Солнышко"] == "_Старт Солнышко"
    assert len(catalog) == 3


def test_match_element_name(ref_env) -> None:
    """Exact, normalized, raw-stem and fuzzy names map onto the catalog."""
    for name in ["Американка", "!_Партнерша_Свитч2", "Катапульта"]:
        write_reference(ref_env["refs"], name, 0.2)
    service = make_service(ref_env)
    catalog = service.get_element_catalog()

    assert service.match_element_name("Американка", catalog) == "Американка"
    assert service.match_element_name("американка", catalog) == "Американка"
    assert service.match_element_name("!_Партнерша_Свитч2", catalog) == "Партнерша Свитч"
    assert service.match_element_name("Партнёрша-свитч", catalog) == "Партнерша Свитч"
    # Short names never fuzzy-match
    assert service.match_element_name("Амерканка", catalog) is None
    assert service.match_element_name("Йо-йо", catalog) is None
    assert service.match_element_name(None, catalog) is None
    assert service.match_element_name("Американка", {}) is None


def test_match_element_name_rejects_false_positives(ref_env) -> None:
    """Real-catalog traps: different short elements must not be merged."""
    for name in ["Раскрытие", "Райд", "Закрытие партнера", "Туннель с выходом через поворот партнера",
                 "Солнышко-Корзинка открытая", "Солнышко-Корзинка закрытая"]:
        write_reference(ref_env["refs"], name, 0.2)
    service = make_service(ref_env)
    catalog = service.get_element_catalog()

    assert service.match_element_name("Закрытие", catalog) is None
    assert service.match_element_name("Рай", catalog) is None
    # Long name with a typo still matches
    assert service.match_element_name(
        "Туннель с выходом через пворот партнера", catalog
    ) == "Туннель с выходом через поворот партнера"
    # Ambiguous between two close names -> None
    assert service.match_element_name("Солнышко-Корзинка ткрытая", catalog) is None


def test_get_reference_resolves_display_name(ref_env) -> None:
    """A normalized display name loads the underlying reference file."""
    write_reference(ref_env["refs"], "!_Партнерша_Свитч2", 0.2)
    ref = make_service(ref_env).get_reference("Партнерша Свитч")
    assert ref is not None
    assert ref["element"] == "!_Партнерша_Свитч2"


# ----------------------------------------------------------------------
# Pose normalization
# ----------------------------------------------------------------------

def test_normalize_pose_is_position_and_scale_invariant() -> None:
    """Shifting and scaling the body does not change the normalized pose."""
    a = normalize_pose(make_landmarks(0.3))
    b = normalize_pose(make_landmarks(0.3, shift=0.2, scale=0.5))
    assert a is not None and b is not None
    assert np.allclose(a, b, atol=1e-5)


def test_normalize_pose_rejects_incomplete() -> None:
    """Missing or degenerate poses are skipped."""
    assert normalize_pose([]) is None
    flat = [{"x": 0.5, "y": 0.5, "z": 0.0, "visibility": 1.0}] * 33
    assert normalize_pose(flat) is None


def test_mirror_poses_twice_is_identity() -> None:
    """Mirroring is its own inverse."""
    pose = normalize_pose(make_landmarks(0.3, lean=0.1))[None]
    assert np.allclose(mirror_poses(mirror_poses(pose)), pose)


# ----------------------------------------------------------------------
# Similarity index
# ----------------------------------------------------------------------

def test_index_is_compact_and_cached_on_disk(ref_env) -> None:
    """The index keeps a fixed number of poses and is written to disk."""
    write_reference(ref_env["refs"], "Американка", 0.3, frames=100)
    index = make_service(ref_env).get_similarity_index()

    assert len(index["Американка"]["poses"]) == INDEX_SAMPLES_PER_ELEMENT
    assert ref_env["index"].exists()

    # A fresh service reads the disk index without parsing reference JSONs
    fresh = make_service(ref_env)
    calls = []
    original = fresh._summarize_reference
    fresh._summarize_reference = lambda p: calls.append(p) or original(p)
    assert "Американка" in fresh.get_similarity_index()
    assert calls == []


def test_index_refreshes_changed_new_and_removed_files(ref_env) -> None:
    """Only new or modified files are re-read; deleted ones drop out."""
    import os

    path_a = write_reference(ref_env["refs"], "Американка", 0.3)
    path_b = write_reference(ref_env["refs"], "Солнышко", -0.3)
    service = make_service(ref_env)
    service.get_similarity_index()

    calls: List[str] = []
    original = service._summarize_reference
    service._summarize_reference = lambda p: calls.append(p.stem) or original(p)

    write_reference(ref_env["refs"], "Американка", 0.5)
    os.utime(path_a, (path_a.stat().st_atime, path_a.stat().st_mtime + 10))
    write_reference(ref_env["refs"], "Катапульта", 0.0)
    path_b.unlink()

    index = service.get_similarity_index()
    assert sorted(calls) == ["Американка", "Катапульта"]
    assert set(index) == {"Американка", "Катапульта"}


def test_index_skips_broken_json(ref_env) -> None:
    """A half-written reference file does not break the index."""
    write_reference(ref_env["refs"], "Американка", 0.3)
    (ref_env["refs"] / "Сломанный.json").write_text("{not json", encoding="utf-8")
    index = make_service(ref_env).get_similarity_index()
    assert set(index) == {"Американка"}


# ----------------------------------------------------------------------
# Candidate selection
# ----------------------------------------------------------------------

def test_find_candidates_ranks_most_similar_first(ref_env) -> None:
    """The element with matching poses ranks first."""
    write_reference(ref_env["refs"], "Руки вверх", 0.4)
    write_reference(ref_env["refs"], "Руки вниз", -0.4)
    write_reference(ref_env["refs"], "Руки в стороны", 0.0)

    candidates = make_service(ref_env).find_candidate_elements(user_poses(0.4), limit=3)

    assert [c["element"] for c in candidates][0] == "Руки вверх"
    assert candidates[0]["score"] < candidates[-1]["score"]
    assert 1 <= len(candidates[0]["timestamps"]) <= 2


def test_find_candidates_matches_mirrored_pose(ref_env) -> None:
    """A dancer facing the other way still matches the element."""
    write_reference(ref_env["refs"], "Асимметрия", 0.3, lean=0.15)
    write_reference(ref_env["refs"], "Руки вниз", -0.4)

    # Mirrored performance: x flips and MediaPipe's left/right labels swap
    swap = {11: 12, 12: 11, 13: 14, 14: 13, 15: 16, 16: 15,
            23: 24, 24: 23, 25: 26, 26: 25, 27: 28, 28: 27}
    mirrored_user = []
    for pose in user_poses(0.3, lean=0.15):
        lms = pose["landmarks"]
        if not lms:
            continue
        flipped = [dict(lms[swap.get(i, i)], x=1.0 - lms[swap.get(i, i)]["x"])
                   for i in range(33)]
        mirrored_user.append(dict(pose, landmarks=flipped))

    service = make_service(ref_env)
    candidates = service.find_candidate_elements(mirrored_user, limit=2)
    assert candidates[0]["element"] == "Асимметрия"
    assert candidates[0]["score"] < 0.05


def test_find_candidates_limit_and_dedup(ref_env) -> None:
    """Variants of one element appear once; the limit is respected."""
    write_reference(ref_env["refs"], "Свитч", 0.4)
    write_reference(ref_env["refs"], "Свитч2", 0.41)
    write_reference(ref_env["refs"], "Руки вниз", -0.4)

    candidates = make_service(ref_env).find_candidate_elements(user_poses(0.4), limit=5)
    names = [c["element"] for c in candidates]
    assert names.count("Свитч") == 1
    assert len(names) == 2

    assert len(make_service(ref_env).find_candidate_elements(user_poses(0.4), limit=1)) == 1


def test_find_candidates_without_user_poses(ref_env) -> None:
    """No usable user poses means no candidates."""
    write_reference(ref_env["refs"], "Свитч", 0.4)
    service = make_service(ref_env)
    assert service.find_candidate_elements([]) == []
    assert service.find_candidate_elements([{"detected": False, "landmarks": []}]) == []


def test_find_candidates_without_references(tmp_path: Path) -> None:
    """A missing reference directory yields no candidates."""
    service = ReferenceService(str(tmp_path / "missing"), index_path=str(tmp_path / "i.json"))
    assert service.find_candidate_elements(user_poses(0.4)) == []


# ----------------------------------------------------------------------
# Example frames
# ----------------------------------------------------------------------

def write_video(path: Path, frames: int = 60, size: Tuple[int, int] = (1280, 720)) -> None:
    """Write a small synthetic video; frame brightness encodes its index."""
    # cv2.VideoWriter cannot write Cyrillic paths on Windows, so write to an
    # ASCII name first and rename
    tmp = path.with_name("tmp_video.mp4")
    writer = cv2.VideoWriter(str(tmp), cv2.VideoWriter_fourcc(*"mp4v"), 30.0, size)
    for i in range(frames):
        frame = np.full((size[1], size[0], 3), i * 4, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    tmp.rename(path)


def test_get_example_frame_downscales_and_caches(ref_env) -> None:
    """Frames come from the source video, are ≤512px and cached on disk."""
    write_video(ref_env["videos"] / "_Старт. Американка.MP4")
    service = make_service(ref_env)

    path = service.get_example_frame("_Старт. Американка", 1.0)
    assert path is not None
    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert max(image.shape[:2]) <= 512
    assert Path(path).parent == ref_env["frames"]

    # Second call is served from the cache even without the video
    (ref_env["videos"] / "_Старт. Американка.MP4").unlink()
    fresh = make_service(ref_env)
    assert fresh.get_example_frame("_Старт. Американка", 1.0) == path


def test_get_example_frame_missing_video(ref_env) -> None:
    """A missing source video yields None, not an exception."""
    assert make_service(ref_env).get_example_frame("Нет такого", 1.0) is None


def test_select_example_frames_respects_budget(ref_env) -> None:
    """Each candidate gets one frame before any gets a second one."""
    for i, raise_ in enumerate([0.4, 0.35, 0.3, -0.4]):
        name = f"Элемент {chr(ord('А') + i)}"
        write_reference(ref_env["refs"], name, raise_)
        write_video(ref_env["videos"] / f"{name}.mp4")
    service = make_service(ref_env)

    examples = service.select_example_frames(
        user_poses(0.4), max_images=5, max_elements=4, frames_per_element=2
    )
    counts = [len(e["frame_paths"]) for e in examples]
    assert sum(counts) == 5
    assert len(examples) == 4
    assert counts[0] == 2

    assert service.select_example_frames(user_poses(0.4), max_images=0) == []
    assert service.select_example_frames(None, max_images=5) == []


def test_select_example_frames_skips_elements_without_video(ref_env) -> None:
    """Candidates whose video is missing are left out."""
    write_reference(ref_env["refs"], "Без видео", 0.4)
    write_reference(ref_env["refs"], "С видео", 0.3)
    write_video(ref_env["videos"] / "С видео.mov")

    examples = make_service(ref_env).select_example_frames(user_poses(0.4), max_images=4)
    assert [e["element"] for e in examples] == ["С видео"]


# ----------------------------------------------------------------------
# Review fixes: aspect ratio, visibility, edge trim, offline build
# ----------------------------------------------------------------------

def to_frame_coords(landmarks: List[Dict[str, float]], width: int, height: int) -> List[Dict[str, float]]:
    """
    Convert isotropic landmarks (x and y in one unit) into MediaPipe frame
    coordinates of a width x height video (x / width, y / height).
    """
    side = float(max(width, height))
    return [
        dict(lm, x=0.5 + (lm["x"] - 0.5) * side / width, y=0.5 + (lm["y"] - 0.5) * side / height)
        for lm in landmarks
    ]


def write_reference_raw(directory: Path, name: str, poses: List[Dict], **extra) -> Path:
    """Write a reference JSON with the given poses and extra top-level fields."""
    data = {"element": name, "total_frames": len(poses), "fps": 30.0,
            "poses_count": len(poses), "poses": poses, **extra}
    path = directory / f"{name}.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_normalize_pose_uses_aspect_ratio() -> None:
    """The same body filmed 9:16 and 16:9 normalizes to the same pose."""
    base = make_landmarks(0.3, lean=0.1, scale=0.5)
    portrait = normalize_pose(to_frame_coords(base, 720, 1280), aspect=720 / 1280)
    landscape = normalize_pose(to_frame_coords(base, 1280, 720), aspect=1280 / 720)
    assert np.allclose(portrait, landscape, atol=1e-4)


def test_candidates_match_across_orientations(ref_env) -> None:
    """A portrait user video matches its landscape reference (width/height in JSON)."""
    own = make_landmarks(0.3, lean=0.1, scale=0.5)
    other = make_landmarks(0.0, scale=0.5)
    for name, base in (("Свой", own), ("Чужой", other)):
        poses = [{"frame": i, "timestamp": i / 30.0, "landmarks": to_frame_coords(base, 1920, 1080)}
                 for i in range(30)]
        write_reference_raw(ref_env["refs"], name, poses, width=1920, height=1080)

    user = [{"frame": i, "timestamp": i / 30.0, "detected": True,
             "landmarks": to_frame_coords(own, 1080, 1920)} for i in range(30)]
    candidates = make_service(ref_env).find_candidate_elements(user, user_aspect=1080 / 1920)

    assert candidates[0]["element"] == "Свой"
    assert candidates[0]["score"] < 0.01


def test_reference_aspect_falls_back_to_video(ref_env) -> None:
    """Without width/height in JSON the aspect is read from the source video."""
    write_reference(ref_env["refs"], "Вертикальное", 0.3)
    write_video(ref_env["videos"] / "Вертикальное.mp4", frames=5, size=(360, 640))

    index = make_service(ref_env).get_similarity_index()
    assert index["Вертикальное"]["aspect"] == pytest.approx(360 / 640, abs=1e-3)


def test_normalize_pose_requires_visible_anchors() -> None:
    """Poses with hidden shoulders or hips are skipped."""
    landmarks = make_landmarks(0.3)
    landmarks[23] = dict(landmarks[23], visibility=0.3)
    assert normalize_pose(landmarks) is None


def test_index_skips_clip_edges(ref_env) -> None:
    """Sampled reference timestamps avoid the first and last seconds."""
    write_reference(ref_env["refs"], "Длинный", 0.3, frames=300)
    timestamps = make_service(ref_env).get_similarity_index()["Длинный"]["timestamps"]
    duration = 299 / 30.0
    assert min(timestamps) >= duration * 0.1
    assert max(timestamps) <= duration * 0.9


def test_build_index_saves_progress(ref_env, monkeypatch) -> None:
    """The index is saved every `save_every` refreshed elements and at the end."""
    for i in range(5):
        write_reference(ref_env["refs"], f"Элемент {chr(ord('А') + i)}", 0.1 * i)
    service = make_service(ref_env)
    saves: List[int] = []
    original = service._save_index_file
    monkeypatch.setattr(service, "_save_index_file",
                        lambda entries: saves.append(len(entries)) or original(entries))

    stats = service.build_index(save_every=2)

    assert saves == [2, 4, 5]
    assert stats["refreshed"] == 5
    assert stats["total"] == 5


def test_index_write_leaves_no_temp_files(ref_env) -> None:
    """Index writes use unique temp files and never touch a foreign .tmp."""
    foreign = ref_env["index"].with_name(ref_env["index"].name + ".tmp")
    foreign.write_text("other worker", encoding="utf-8")
    write_reference(ref_env["refs"], "Американка", 0.3)

    make_service(ref_env).get_similarity_index()

    leftovers = [p.name for p in ref_env["index"].parent.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == [foreign.name]
    assert foreign.read_text(encoding="utf-8") == "other worker"


def test_build_reference_index_function(ref_env) -> None:
    """The public offline builder creates the index file."""
    from app.services.reference_service import build_reference_index

    write_reference(ref_env["refs"], "Американка", 0.3)
    stats = build_reference_index(str(ref_env["refs"]), index_path=str(ref_env["index"]),
                                  videos_dir=str(ref_env["videos"]))
    assert stats["refreshed"] == 1
    assert Path(stats["index_path"]) == ref_env["index"]
    assert ref_env["index"].exists()


def test_build_reference_index_cli(ref_env) -> None:
    """The CLI script builds the index and exits cleanly."""
    import subprocess
    import sys

    write_reference(ref_env["refs"], "Американка", 0.3)
    script = Path(__file__).resolve().parent.parent / "scripts" / "build_reference_index.py"
    result = subprocess.run(
        [sys.executable, str(script), "--reference-dir", str(ref_env["refs"]),
         "--index-path", str(ref_env["index"]), "--videos-dir", str(ref_env["videos"])],
        capture_output=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert ref_env["index"].exists()


def test_one_failing_frame_keeps_other_examples(ref_env, monkeypatch) -> None:
    """An exception for one element's frame does not drop the rest."""
    write_reference(ref_env["refs"], "Хороший", 0.4)
    write_reference(ref_env["refs"], "Плохой", 0.38)
    service = make_service(ref_env)

    def fake_frame(stem, timestamp, max_side=512):
        if stem == "Плохой":
            raise RuntimeError("decoder crashed")
        return f"{stem}-{timestamp}.jpg"

    monkeypatch.setattr(service, "get_example_frame", fake_frame)
    examples = service.select_example_frames(user_poses(0.4), max_images=4)
    assert [e["element"] for e in examples] == ["Хороший"]


def test_soft_time_limit_is_not_swallowed(ref_env, monkeypatch) -> None:
    """Celery's soft time limit propagates out of example selection."""
    from celery.exceptions import SoftTimeLimitExceeded

    write_reference(ref_env["refs"], "Хороший", 0.4)
    service = make_service(ref_env)

    def timeout(*args, **kwargs):
        raise SoftTimeLimitExceeded()

    monkeypatch.setattr(service, "get_example_frame", timeout)
    with pytest.raises(SoftTimeLimitExceeded):
        service.select_example_frames(user_poses(0.4), max_images=4)


def test_find_reference_video_prefers_mp4(ref_env) -> None:
    """With duplicates, .mp4 wins over .mov regardless of case."""
    for ext in (".MOV", ".mp4"):
        (ref_env["videos"] / f"Дубль{ext}").write_bytes(b"x")
    assert make_service(ref_env).find_reference_video("Дубль").suffix == ".mp4"


def test_default_paths_do_not_depend_on_cwd(monkeypatch, tmp_path) -> None:
    """Relative path settings resolve from backend/, not the working directory."""
    from app.config import settings
    from app.services import reference_service as module

    monkeypatch.setattr(settings, "REFERENCE_VIDEOS_FOLDER", "../hasl_files")
    monkeypatch.chdir(tmp_path)
    service = ReferenceService(str(tmp_path / "refs"))
    assert service.videos_dir.is_absolute()
    assert service.videos_dir == (module.BACKEND_DIR / "../hasl_files").resolve()
