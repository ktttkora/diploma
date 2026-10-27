"""
Reference poses service.

Loads and manages pre-processed reference dance element poses
from JSON files in backend/data/reference_poses/.

Also provides what the AI needs to recognize elements: a catalog of
element names, a compact pose index for cheap similarity search and
downscaled example frames from the source reference videos.
"""

import difflib
import hashlib
import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    from celery.exceptions import SoftTimeLimitExceeded
    # Must never be swallowed by best-effort error handling
    PASSTHROUGH_EXCEPTIONS: Tuple[type, ...] = (SoftTimeLimitExceeded,)
except ImportError:  # pragma: no cover - celery is a project dependency
    PASSTHROUGH_EXCEPTIONS = ()

# backend/ directory, used to resolve relative path settings independent of cwd
BACKEND_DIR = Path(__file__).resolve().parents[2]

# Body landmarks used for pose similarity (face and finger points are noisy)
SIMILARITY_KEYPOINTS: List[int] = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]

# Shoulders and hips define the normalization frame and must be visible
ANCHOR_KEYPOINTS: List[int] = [11, 12, 23, 24]
MIN_ANCHOR_VISIBILITY = 0.5

# Left/right landmark pairs, used to build a mirrored pose
MIRROR_PAIRS: List[Tuple[int, int]] = [
    (11, 12), (13, 14), (15, 16), (23, 24), (25, 26), (27, 28)
]

# Poses sampled per reference element into the compact similarity index
INDEX_SAMPLES_PER_ELEMENT = 24

# Share of usable poses skipped at each end of a reference clip
# (intro/outro standing poses, black frames)
INDEX_EDGE_TRIM = 0.12

# Index is saved after this many refreshed elements, so an interrupted
# build keeps its progress
INDEX_SAVE_EVERY = 50

# Poses sampled from the user video for similarity search
USER_SAMPLES = 60

# Bump when the index layout or normalization changes
INDEX_VERSION = 2

# Preferred first when one element has several source videos
REFERENCE_VIDEO_EXTENSIONS = (".mp4", ".mov")

# Fuzzy name matching: only long names, strict ratio, clear winner
FUZZY_MIN_LENGTH = 10
FUZZY_CUTOFF = 0.9
FUZZY_MARGIN = 0.05

# Teachers named in dataset file names ("Катапульта. Свителев",
# "БэкСпин 2 руки (Тагиров)"); they are not part of the element name
AUTHOR_NAMES = {
    "арутинян", "володя", "володя-лиза", "гринвальд", "даня", "дима", "егор",
    "ермаков", "инна", "костя", "кудрявцев", "лиза", "макарчук", "мятова",
    "николаева", "параход", "пильгун", "рома", "свителев", "скориков",
    "сухарева", "тагиров", "чупина",
}

# Descriptive tails that do not change the element ("Дак. Кратко")
NOISE_TAILS = {"подробно", "кратко", "описание", "полное руководство"}

# Leading markers in dataset file names ("!_", "_")
_PREFIX_RE = re.compile(r"^[!_\s]+")
# Variant suffixes: "Свитч2", "Свивлы (Американка)-1", "Харлей #2", " v2"
_VARIANT_RE = re.compile(r"[\s\-]*(?:#|v)?\d+$", re.IGNORECASE)
# Bracketed notes anywhere: "[3 варианта]"
_BRACKETS_RE = re.compile(r"\s*\[[^\]]*\]")
# Numbered copies: "Крабики (Фаст) (1)"
_COPY_NUMBER_RE = re.compile(r"\s*\(\d+\)$")
# "Радуга. Твист. 2 варианта"
_VARIANT_COUNT_RE = re.compile(r"\.\s*\d+\s+вариант\w*$", re.IGNORECASE)
# Trailing parenthesized word: "(Тагиров)"
_PAREN_TAIL_RE = re.compile(r"\s*\(([^()]*)\)$")
# Trailing ". <tail>" segment
_DOT_TAIL_RE = re.compile(r"\.\s+([^.]+)$")
# Non-alphanumeric characters, dropped from comparison keys
_NON_ALNUM_RE = re.compile(r"[\W_]+", re.UNICODE)


def _strip_name_tail(name: str) -> str:
    """Remove one trailing author/noise/variant marker, if present."""
    for regex in (_COPY_NUMBER_RE, _VARIANT_COUNT_RE):
        stripped = regex.sub("", name)
        if stripped != name:
            return stripped

    paren = _PAREN_TAIL_RE.search(name)
    if paren and paren.group(1).strip().lower() in AUTHOR_NAMES:
        return name[:paren.start()]

    dot = _DOT_TAIL_RE.search(name)
    if dot:
        tail = _VARIANT_RE.sub("", dot.group(1)).strip(" -").lower()
        if tail in AUTHOR_NAMES or tail in NOISE_TAILS:
            return name[:dot.start()]

    for noise in NOISE_TAILS:
        if name.lower().endswith(" " + noise):
            return name[:-len(noise) - 1]

    # Author after a plain separator: "Йо-Йо_Макарчук" -> "Йо-Йо Макарчук"
    head, _, last = name.rpartition(" ")
    if head and last.lower() in AUTHOR_NAMES:
        return head

    stripped = _VARIANT_RE.sub("", name)
    return stripped if stripped.strip(" -.") else name


def normalize_element_name(name: str) -> str:
    """
    Turn a reference file name into a human-readable element name.

    Strips leading "!_"/"_" markers, underscores, bracketed notes, numeric
    variant suffixes, teacher names and descriptive tails ("Подробно"),
    so "!_Партнерша_Свитч2" becomes "Партнерша Свитч" and
    "Катапульта. Свителев" becomes "Катапульта".

    Args:
        name: Raw element name (reference file stem)

    Returns:
        Normalized display name (falls back to the stripped raw name)
    """
    cleaned = _PREFIX_RE.sub("", name).replace("_", " ")
    cleaned = _BRACKETS_RE.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Tails can stack: "Препы-Выпад. Свителев-2", "Крабики (Фаст) (1)"
    for _ in range(5):
        stripped = _strip_name_tail(cleaned).strip(" -.")
        if not stripped or stripped == cleaned:
            break
        cleaned = stripped

    return cleaned or name.strip()


def name_key(name: str) -> str:
    """
    Comparison key for element names.

    Lowercases, maps "ё" to "е" and drops spaces and punctuation, so
    "РолИн-РолАут" and "ролин ролаут" compare equal.

    Args:
        name: Element name

    Returns:
        Normalized key
    """
    return _NON_ALNUM_RE.sub("", name.lower().replace("ё", "е"))


def normalize_pose(
    landmarks: List[Dict[str, float]],
    aspect: float = 1.0
) -> Optional[np.ndarray]:
    """
    Normalize a MediaPipe pose for position- and scale-invariant comparison.

    MediaPipe divides x by frame width and y by frame height, so x is first
    multiplied by the aspect ratio to get isotropic coordinates. Then the
    pose is centered on the hip midpoint and scaled by torso length
    (shoulder midpoint to hip midpoint).

    Args:
        landmarks: 33 MediaPipe landmarks with x, y and optional visibility
        aspect: Frame width / height of the video the pose came from

    Returns:
        Array of shape (len(SIMILARITY_KEYPOINTS), 2), or None if the pose
        is incomplete, degenerate, or its shoulders/hips are not visible
    """
    if not landmarks or len(landmarks) < 33:
        return None
    try:
        xy = np.array([[lm["x"], lm["y"]] for lm in landmarks], dtype=np.float32)
        visibility = [float(landmarks[i].get("visibility", 1.0)) for i in ANCHOR_KEYPOINTS]
    except (KeyError, TypeError, ValueError, AttributeError):
        return None

    if min(visibility) < MIN_ANCHOR_VISIBILITY:
        return None

    if aspect and np.isfinite(aspect) and aspect > 0:
        xy[:, 0] *= aspect

    hip = (xy[23] + xy[24]) / 2.0
    shoulder = (xy[11] + xy[12]) / 2.0
    torso = float(np.linalg.norm(shoulder - hip))
    if not np.isfinite(torso) or torso < 1e-3:
        return None

    return (xy[SIMILARITY_KEYPOINTS] - hip) / torso


def _mirror_order() -> List[int]:
    """Column order of SIMILARITY_KEYPOINTS after a left/right swap."""
    swap: Dict[int, int] = {}
    for left, right in MIRROR_PAIRS:
        swap[left], swap[right] = right, left
    return [SIMILARITY_KEYPOINTS.index(swap.get(k, k)) for k in SIMILARITY_KEYPOINTS]


_MIRROR_ORDER = _mirror_order()


def mirror_poses(poses: np.ndarray) -> np.ndarray:
    """
    Mirror normalized poses horizontally (swap sides, flip x).

    Dancers face either way, so similarity is checked against both.

    Args:
        poses: Array of shape (N, K, 2)

    Returns:
        Mirrored array of the same shape
    """
    mirrored = poses[:, _MIRROR_ORDER, :].copy()
    mirrored[..., 0] *= -1.0
    return mirrored


def _sample_evenly(items: List[Any], count: int) -> List[Any]:
    """Pick up to `count` evenly spaced items, keeping their order."""
    if len(items) <= count:
        return list(items)
    idx = np.linspace(0, len(items) - 1, count).round().astype(int)
    return [items[i] for i in idx]


def _trim_edges(items: List[Any], ratio: float = INDEX_EDGE_TRIM, min_keep: int = 3) -> List[Any]:
    """Drop `ratio` of items at each end, unless too few would remain."""
    cut = int(len(items) * ratio)
    trimmed = items[cut:len(items) - cut] if cut else items
    return trimmed if len(trimmed) >= min_keep else items


def get_video_aspect(video_path: str) -> Optional[float]:
    """
    Get the width / height ratio of the frames OpenCV decodes from a video.

    A frame is read instead of trusting container metadata, so rotated
    phone videos report the orientation MediaPipe actually sees.

    Args:
        video_path: Path to video file

    Returns:
        Aspect ratio, or None if the video cannot be read
    """
    import cv2

    cap = cv2.VideoCapture(str(video_path))
    try:
        if not cap.isOpened():
            return None
        ok, frame = cap.read()
        if ok and frame is not None:
            height, width = frame.shape[:2]
        else:
            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    finally:
        cap.release()

    if not width or not height:
        return None
    return float(width) / float(height)


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """
    Write a file atomically through a unique temp file in the same directory.

    Unique names keep parallel workers from clobbering each other's
    temp files; os.replace makes the final write atomic.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp_name, path)
    except BaseException:
        # Clean up our own temp file; the target stays untouched
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


class ReferenceService:
    """Service for working with reference dance element poses."""

    def __init__(
        self,
        reference_dir: str = "data/reference_poses",
        videos_dir: Optional[str] = None,
        frames_dir: Optional[str] = None,
        index_path: Optional[str] = None
    ):
        """
        Initialize reference service.

        Args:
            reference_dir: Directory with reference JSON files
            videos_dir: Directory with source reference videos
                (defaults to settings.REFERENCE_VIDEOS_FOLDER)
            frames_dir: Cache directory for extracted example frames
                (defaults to settings.REFERENCE_FRAMES_FOLDER)
            index_path: Path of the compact similarity index file
                (defaults to settings.REFERENCE_INDEX_PATH)
        """
        self.reference_dir = Path(reference_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._videos_dir = Path(videos_dir) if videos_dir else None
        self._frames_dir = Path(frames_dir) if frames_dir else None
        self._index_path = Path(index_path) if index_path else None
        self._index: Optional[Dict[str, Dict[str, Any]]] = None
        self._video_lookup: Optional[Dict[str, Path]] = None

    @staticmethod
    def _setting_path(name: str, default: str) -> Path:
        """
        Read a path setting lazily, resolving relative paths from backend/.

        Lazy, so importing this module needs no .env; resolved from the
        source tree, so the result does not depend on the working directory.
        """
        value = default
        try:
            from app.config import settings
            value = str(getattr(settings, name, default) or default)
        except Exception:
            pass
        path = Path(value)
        return path if path.is_absolute() else (BACKEND_DIR / path).resolve()

    @property
    def videos_dir(self) -> Path:
        """Directory with source reference videos."""
        if self._videos_dir is None:
            self._videos_dir = self._setting_path("REFERENCE_VIDEOS_FOLDER", "../hasl_files")
        return self._videos_dir

    @property
    def frames_dir(self) -> Path:
        """Cache directory for extracted example frames."""
        if self._frames_dir is None:
            self._frames_dir = self._setting_path("REFERENCE_FRAMES_FOLDER", "data/reference_frames")
        return self._frames_dir

    @property
    def index_path(self) -> Path:
        """Path of the compact similarity index file."""
        if self._index_path is None:
            self._index_path = self._setting_path("REFERENCE_INDEX_PATH", "data/reference_index.json")
        return self._index_path

    def list_available_elements(self) -> List[str]:
        """
        List all available reference dance elements.

        Returns:
            List of element names
        """
        if not self.reference_dir.exists():
            return []

        elements = []
        for json_file in self.reference_dir.glob("*.json"):
            elements.append(json_file.stem)

        return sorted(elements)

    def get_reference(self, element_name: str) -> Optional[Dict[str, Any]]:
        """
        Load reference poses for a dance element.

        Uses in-memory cache for repeated access. Accepts both file stems and
        normalized display names from get_element_catalog.

        Args:
            element_name: Name of dance element

        Returns:
            Dict with element, total_frames, fps, poses, or None if not found
        """
        # Check cache first
        if element_name in self._cache:
            return self._cache[element_name]

        json_path = self.reference_dir / f"{element_name}.json"
        if not json_path.exists():
            # The AI and the results page use normalized display names
            stem = self.get_element_catalog().get(element_name)
            if not stem or stem == element_name:
                return None
            return self.get_reference(stem)

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._cache[element_name] = data
            return data
        except (json.JSONDecodeError, IOError):
            return None

    def find_similar_pose(
        self,
        element_name: str,
        target_timestamp: float
    ) -> Optional[Dict[str, Any]]:
        """
        Find reference pose closest to given timestamp.

        Args:
            element_name: Name of dance element
            target_timestamp: Target timestamp in seconds

        Returns:
            Pose dict with frame, timestamp, landmarks, or None
        """
        reference = self.get_reference(element_name)
        if not reference or not reference.get("poses"):
            return None

        poses = reference["poses"]
        closest = min(poses, key=lambda p: abs(p["timestamp"] - target_timestamp))
        return closest

    def get_reference_frame_at_ratio(
        self,
        element_name: str,
        ratio: float
    ) -> Optional[Dict[str, Any]]:
        """
        Get reference pose at relative position in element (0.0-1.0).

        Useful when user video and reference have different durations.

        Args:
            element_name: Name of dance element
            ratio: Relative position (0.0 = start, 1.0 = end)

        Returns:
            Pose dict or None
        """
        reference = self.get_reference(element_name)
        if not reference or not reference.get("poses"):
            return None

        poses = reference["poses"]
        idx = int(len(poses) * max(0.0, min(1.0, ratio)))
        idx = min(idx, len(poses) - 1)
        return poses[idx]

    def clear_cache(self) -> None:
        """Clear in-memory reference cache."""
        self._cache.clear()
        self._index = None
        self._video_lookup = None

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about loaded references.

        Returns:
            Dict with total_elements, cached_count, total_poses
        """
        elements = self.list_available_elements()
        total_poses = 0
        for el in elements:
            ref = self.get_reference(el)
            if ref:
                total_poses += ref.get("poses_count", 0)

        return {
            "total_elements": len(elements),
            "cached_count": len(self._cache),
            "total_poses": total_poses,
            "elements": elements
        }

    # ------------------------------------------------------------------
    # Element names
    # ------------------------------------------------------------------

    def get_element_catalog(self) -> Dict[str, str]:
        """
        Map normalized display names to reference file stems.

        Variants that normalize to the same name ("Свитч", "Свитч2",
        "Катапульта. Свителев") collapse into one entry, so every display
        name points at exactly one file. The canonical stem is the one that
        needed the least cleanup (equal to the display name, then shortest).

        Returns:
            Dict {display_name: stem}, sorted by display name
        """
        # Group by comparison key, so names differing only in case or
        # punctuation ("Крабики (Фаст)" / "Крабики (фаст)") become one entry
        groups: Dict[str, List[str]] = {}
        for stem in self.list_available_elements():
            groups.setdefault(name_key(normalize_element_name(stem)), []).append(stem)

        catalog: Dict[str, str] = {}
        for stems in groups.values():
            canonical = min(
                stems,
                key=lambda s: (s != normalize_element_name(s), len(s), s)
            )
            catalog[normalize_element_name(canonical)] = canonical
        return dict(sorted(catalog.items()))

    def match_element_name(
        self,
        name: Optional[str],
        catalog: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Map an element name returned by the AI onto the catalog.

        Tries an exact match on the normalized key (case, "ё", spaces and
        punctuation ignored), for the name as given and after display-name
        normalization. Fuzzy matching (difflib) is used only for names of at
        least FUZZY_MIN_LENGTH characters, with a strict cutoff and a clear
        margin over the runner-up; short names like "Рай" never fuzzy-match.

        Args:
            name: Element name from the AI response
            catalog: Catalog from get_element_catalog (built if omitted)

        Returns:
            Display name from the catalog, or None if nothing matches safely
        """
        if not name or not isinstance(name, str):
            return None
        if catalog is None:
            catalog = self.get_element_catalog()
        if not catalog:
            return None

        candidate = name.strip()
        if candidate in catalog:
            return candidate

        by_key: Dict[str, str] = {}
        for display, stem in catalog.items():
            by_key.setdefault(name_key(display), display)
            by_key.setdefault(name_key(stem), display)

        for variant in (candidate, normalize_element_name(candidate)):
            key = name_key(variant)
            if key and key in by_key:
                return by_key[key]

        key = name_key(normalize_element_name(candidate))
        if len(key) < FUZZY_MIN_LENGTH:
            return None

        scores = sorted(
            (
                (difflib.SequenceMatcher(None, key, other).ratio(), other)
                for other in by_key
            ),
            reverse=True,
        )
        if not scores or scores[0][0] < FUZZY_CUTOFF:
            return None
        best_ratio, best_key = scores[0]
        best_display = by_key[best_key]
        runner_up = next(
            (ratio for ratio, other in scores[1:] if by_key[other] != best_display),
            0.0,
        )
        if best_ratio - runner_up < FUZZY_MARGIN:
            return None
        return best_display

    # ------------------------------------------------------------------
    # Compact similarity index
    # ------------------------------------------------------------------

    def _reference_aspect(self, data: Dict[str, Any], stem: str) -> Optional[float]:
        """
        Aspect ratio of a reference video.

        Uses width/height from the JSON when present, otherwise reads a frame
        of the source video.
        """
        try:
            width = float(data.get("width") or 0)
            height = float(data.get("height") or 0)
        except (TypeError, ValueError):
            width = height = 0.0
        if width > 0 and height > 0:
            return width / height

        video_path = self.find_reference_video(stem)
        if video_path is None:
            return None
        return get_video_aspect(str(video_path))

    def _summarize_reference(self, json_path: Path) -> Optional[Dict[str, Any]]:
        """
        Build the index entry for one reference JSON file.

        The full file is read once and only INDEX_SAMPLES_PER_ELEMENT
        normalized poses are kept (the first and last INDEX_EDGE_TRIM of the
        clip are skipped); the file is not added to the in-memory cache.

        Args:
            json_path: Reference JSON file

        Returns:
            Index entry {mtime, size, aspect, timestamps, poses}, with empty
            lists when the file has too few usable poses, or None on read errors
        """
        stat = json_path.stat()
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            logger.warning("Skipping unreadable reference %s: %s", json_path.name, exc)
            return None

        aspect = self._reference_aspect(data, json_path.stem)
        if aspect is None:
            logger.warning(
                "Unknown aspect ratio for reference %s, assuming square pixels",
                json_path.name
            )

        usable: List[Tuple[float, np.ndarray]] = []
        for pose in data.get("poses") or []:
            normalized = normalize_pose(pose.get("landmarks") or [], aspect or 1.0)
            if normalized is not None:
                usable.append((float(pose.get("timestamp", 0.0)), normalized))

        sampled = _sample_evenly(_trim_edges(usable), INDEX_SAMPLES_PER_ELEMENT)
        return {
            "mtime": stat.st_mtime,
            "size": stat.st_size,
            "aspect": round(aspect, 4) if aspect else None,
            "timestamps": [round(ts, 3) for ts, _ in sampled],
            "poses": [np.round(p, 4).tolist() for _, p in sampled],
        }

    def _load_index_file(self) -> Dict[str, Dict[str, Any]]:
        """Read the on-disk index, returning {} if missing or outdated."""
        if not self.index_path.exists():
            return {}
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            logger.warning("Reference index is unreadable, rebuilding: %s", exc)
            return {}
        if payload.get("version") != INDEX_VERSION:
            return {}
        entries = payload.get("elements")
        return entries if isinstance(entries, dict) else {}

    def _save_index_file(self, entries: Dict[str, Dict[str, Any]]) -> None:
        """Write the index atomically through a unique temp file."""
        payload = json.dumps(
            {"version": INDEX_VERSION, "elements": entries},
            ensure_ascii=False, separators=(",", ":")
        )
        _atomic_write_bytes(self.index_path, payload.encode("utf-8"))

    def _try_save_index(self, entries: Dict[str, Dict[str, Any]]) -> None:
        """Save the index, logging instead of failing on disk errors."""
        try:
            self._save_index_file(entries)
        except OSError as exc:
            logger.warning("Could not save reference index: %s", exc)

    def build_index(
        self,
        save_every: int = INDEX_SAVE_EVERY,
        progress: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Bring the compact pose index up to date with the reference JSONs.

        Only new or modified files (by mtime and size) are re-read, entries
        of removed files are dropped, and the index is saved every
        `save_every` refreshed elements so an interrupted build keeps its
        progress.

        Args:
            save_every: Save after this many refreshed elements
            progress: Optional callback(done, total, stem) per refreshed element

        Returns:
            Stats {total, refreshed, removed, failed}
        """
        stats = {"total": 0, "refreshed": 0, "removed": 0, "failed": 0}
        if self._index is None:
            self._index = self._load_index_file()
        entries = self._index

        if not self.reference_dir.exists():
            return stats

        current = {p.stem: p for p in self.reference_dir.glob("*.json")}
        stats["total"] = len(current)

        for stem in list(entries):
            if stem not in current:
                del entries[stem]
                stats["removed"] += 1

        stale = []
        for stem, path in sorted(current.items()):
            stat = path.stat()
            entry = entries.get(stem)
            if entry and entry.get("mtime") == stat.st_mtime and entry.get("size") == stat.st_size:
                continue
            stale.append((stem, path))

        unsaved = stats["removed"]
        for done, (stem, path) in enumerate(stale, start=1):
            summary = self._summarize_reference(path)
            if summary is None:
                stats["failed"] += 1
            else:
                entries[stem] = summary
                stats["refreshed"] += 1
                unsaved += 1
            if progress:
                progress(done, len(stale), stem)
            if save_every > 0 and unsaved >= save_every:
                self._try_save_index(entries)
                unsaved = 0

        if unsaved:
            self._try_save_index(entries)
        if stats["refreshed"] or stats["removed"]:
            logger.info(
                "Reference index: refreshed %d, removed %d, failed %d of %d elements",
                stats["refreshed"], stats["removed"], stats["failed"], stats["total"]
            )
        return stats

    def get_similarity_index(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the compact pose index, refreshing entries whose JSON changed.

        Returns:
            Dict {stem: {mtime, size, aspect, timestamps, poses}}
        """
        if not self.reference_dir.exists():
            return {}
        self.build_index()
        return self._index or {}

    # ------------------------------------------------------------------
    # Candidate selection
    # ------------------------------------------------------------------

    @staticmethod
    def _user_pose_matrix(
        user_poses: List[Dict[str, Any]],
        aspect: float = 1.0
    ) -> Optional[np.ndarray]:
        """Normalize and sample user poses into an (N, K, 2) array."""
        normalized = []
        for pose in user_poses or []:
            if pose.get("detected") is False:
                continue
            arr = normalize_pose(pose.get("landmarks") or [], aspect)
            if arr is not None:
                normalized.append(arr)
        if not normalized:
            return None
        return np.stack(_sample_evenly(normalized, USER_SAMPLES))

    @staticmethod
    def _pick_spread(distances: np.ndarray, count: int) -> List[int]:
        """
        Pick indices of the best-matching reference poses, spread in time.

        Args:
            distances: Per reference pose distance to the user, shape (R,)
            count: How many indices to pick

        Returns:
            Indices sorted by time
        """
        min_gap = max(1, len(distances) // 4)
        picked: List[int] = []
        for idx in np.argsort(distances):
            if all(abs(int(idx) - p) >= min_gap for p in picked):
                picked.append(int(idx))
            if len(picked) >= count:
                break
        return sorted(picked)

    def find_candidate_elements(
        self,
        user_poses: List[Dict[str, Any]],
        limit: int = 8,
        frames_per_element: int = 2,
        user_aspect: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Rank reference elements by pose similarity to the user video.

        Score is the mean, over the sampled reference poses, of the distance
        to the nearest sampled user pose (mirrored poses included), in torso
        lengths. Lower means more similar. Works on the compact index only.

        Args:
            user_poses: Poses from PoseService.extract_poses_from_video
            limit: Maximum number of elements to return
            frames_per_element: Example timestamps to pick per element
            user_aspect: Frame width / height of the user video

        Returns:
            List of {element, stem, score, timestamps}, best first;
            one entry per display name
        """
        user = self._user_pose_matrix(user_poses, user_aspect or 1.0)
        if user is None or limit <= 0:
            return []

        user_both = np.concatenate([user, mirror_poses(user)])  # (2U, K, 2)
        index = self.get_similarity_index()
        display_by_key = {name_key(d): d for d in self.get_element_catalog()}

        scored: List[Dict[str, Any]] = []
        for stem, entry in index.items():
            poses = entry.get("poses") or []
            if len(poses) < 3:
                continue
            ref = np.asarray(poses, dtype=np.float32)  # (R, K, 2)
            if ref.ndim != 3 or ref.shape[1:] != user.shape[1:]:
                continue

            # (R, 2U): mean keypoint distance between every pair of poses
            pair = np.linalg.norm(ref[:, None, :, :] - user_both[None, :, :, :], axis=-1).mean(axis=-1)
            nearest = pair.min(axis=1)
            picks = self._pick_spread(nearest, frames_per_element)
            timestamps = entry.get("timestamps") or []
            scored.append({
                "element": display_by_key.get(
                    name_key(normalize_element_name(stem)), normalize_element_name(stem)
                ),
                "stem": stem,
                "score": round(float(nearest.mean()), 4),
                "timestamps": [timestamps[i] for i in picks if i < len(timestamps)],
            })

        scored.sort(key=lambda c: c["score"])

        unique: List[Dict[str, Any]] = []
        seen = set()
        for cand in scored:
            if cand["element"] in seen:
                continue
            seen.add(cand["element"])
            unique.append(cand)
            if len(unique) >= limit:
                break
        return unique

    # ------------------------------------------------------------------
    # Example frames
    # ------------------------------------------------------------------

    def find_reference_video(self, stem: str) -> Optional[Path]:
        """
        Find the source video of a reference element.

        When an element has several videos, .mp4 wins over .mov (the same
        rule the reference extraction script uses for duplicates).

        Args:
            stem: Reference file stem (= source video name without extension)

        Returns:
            Path to the video, or None if it is missing
        """
        if self._video_lookup is None:
            lookup: Dict[str, Path] = {}
            if self.videos_dir.exists():
                ranked = sorted(
                    (
                        p for p in self.videos_dir.iterdir()
                        if p.suffix.lower() in REFERENCE_VIDEO_EXTENSIONS
                    ),
                    key=lambda p: (REFERENCE_VIDEO_EXTENSIONS.index(p.suffix.lower()), p.name),
                )
                for path in ranked:
                    lookup.setdefault(path.stem, path)
            self._video_lookup = lookup
        return self._video_lookup.get(stem)

    def get_example_frame(
        self,
        stem: str,
        timestamp: float,
        max_side: int = 512
    ) -> Optional[str]:
        """
        Get a downscaled JPEG frame of a reference video, cached on disk.

        Cache file names are hashes, so Cyrillic element names never reach
        OpenCV write paths.

        Args:
            stem: Reference file stem
            timestamp: Frame time in seconds
            max_side: Longest side of the saved frame in pixels

        Returns:
            Path to the JPEG, or None if the frame cannot be extracted
        """
        key = hashlib.sha1(f"{stem}|{timestamp:.3f}|{max_side}".encode("utf-8")).hexdigest()[:20]
        frame_path = self.frames_dir / f"{key}.jpg"
        if frame_path.exists() and frame_path.stat().st_size > 0:
            return str(frame_path)

        video_path = self.find_reference_video(stem)
        if video_path is None:
            logger.warning("Reference video not found for %s", stem)
            return None

        import cv2

        cap = cv2.VideoCapture(str(video_path))
        try:
            if not cap.isOpened():
                logger.warning("Cannot open reference video %s", video_path.name)
                return None
            cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, timestamp) * 1000.0)
            ok, frame = cap.read()
        finally:
            cap.release()

        if not ok or frame is None:
            logger.warning("Cannot read frame at %.2fs from %s", timestamp, video_path.name)
            return None

        height, width = frame.shape[:2]
        scale = max_side / float(max(height, width))
        if scale < 1.0:
            frame = cv2.resize(
                frame, (int(width * scale), int(height * scale)),
                interpolation=cv2.INTER_AREA
            )

        success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not success:
            return None

        _atomic_write_bytes(frame_path, buffer.tobytes())
        return str(frame_path)

    def select_example_frames(
        self,
        user_poses: Optional[List[Dict[str, Any]]],
        max_images: int,
        max_elements: int = 8,
        frames_per_element: int = 2,
        max_side: int = 512,
        user_aspect: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Pick example frames of the reference elements closest to the user.

        Every candidate gets one frame first; leftover budget goes to second
        frames, so the AI sees more elements rather than more angles. A frame
        that fails to extract is skipped without affecting the others.

        Args:
            user_poses: Poses of the user video
            max_images: Total example frame budget
            max_elements: Maximum number of candidate elements
            frames_per_element: Maximum frames per element
            max_side: Longest side of example frames in pixels
            user_aspect: Frame width / height of the user video

        Returns:
            List of {element, stem, score, frame_paths}, best first
        """
        if not user_poses or max_images <= 0 or frames_per_element <= 0:
            return []

        n_elements = min(max_elements, max_images)
        candidates = self.find_candidate_elements(
            user_poses, limit=n_elements, frames_per_element=frames_per_element,
            user_aspect=user_aspect
        )

        examples: List[Dict[str, Any]] = [
            {"element": c["element"], "stem": c["stem"], "score": c["score"], "frame_paths": []}
            for c in candidates
        ]
        budget = max_images
        for round_idx in range(frames_per_element):
            for cand, example in zip(candidates, examples):
                if budget <= 0:
                    break
                if round_idx >= len(cand["timestamps"]):
                    continue
                try:
                    path = self.get_example_frame(
                        cand["stem"], cand["timestamps"][round_idx], max_side=max_side
                    )
                except PASSTHROUGH_EXCEPTIONS:
                    raise
                except Exception as exc:
                    logger.warning("Example frame failed for %s: %s", cand["stem"], exc)
                    path = None
                if path:
                    example["frame_paths"].append(path)
                    budget -= 1

        return [e for e in examples if e["frame_paths"]]


def build_reference_index(
    reference_dir: str = "data/reference_poses",
    index_path: Optional[str] = None,
    videos_dir: Optional[str] = None,
    save_every: int = INDEX_SAVE_EVERY,
    progress: Optional[Callable[[int, int, str], None]] = None
) -> Dict[str, Any]:
    """
    Build or refresh the compact reference pose index offline.

    Args:
        reference_dir: Directory with reference JSON files
        index_path: Index file (defaults to settings.REFERENCE_INDEX_PATH)
        videos_dir: Source videos, used when a JSON has no width/height
        save_every: Save after this many refreshed elements
        progress: Optional callback(done, total, stem)

    Returns:
        Stats {total, refreshed, removed, failed, index_path}
    """
    service = ReferenceService(reference_dir, videos_dir=videos_dir, index_path=index_path)
    stats = service.build_index(save_every=save_every, progress=progress)
    stats["index_path"] = str(service.index_path)
    return stats


# Singleton instance
reference_service = ReferenceService()
