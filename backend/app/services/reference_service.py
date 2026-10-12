"""
Reference poses service.

Loads and manages pre-processed reference dance element poses
from JSON files in backend/data/reference_poses/.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any


class ReferenceService:
    """Service for working with reference dance element poses."""

    def __init__(self, reference_dir: str = "data/reference_poses"):
        """
        Initialize reference service.

        Args:
            reference_dir: Directory with reference JSON files
        """
        self.reference_dir = Path(reference_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}

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

        Uses in-memory cache for repeated access.

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
            return None

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


# Singleton instance
reference_service = ReferenceService()
