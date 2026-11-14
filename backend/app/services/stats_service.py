"""
Progress statistics for a user's saved analyses.

Averages, the three most common error types, and the score timeline
used by the profile page.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.analysis import Analysis, AnalysisStatus
from app.models.error import Error
from app.models.video import Video


def _mean(values: List[Optional[float]]) -> Optional[float]:
    """
    Average the values that are present.

    Args:
        values: Scores, some of which may be missing

    Returns:
        Rounded mean, or None when every value is missing
    """
    present = [value for value in values if value is not None]
    if not present:
        return None
    return round(sum(present) / len(present), 1)


def build_user_stats(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Build progress statistics from the user's saved, completed analyses.

    Args:
        db: Database session
        user_id: Owner whose analyses are included

    Returns:
        Averages, up to three most frequent error types, and a
        chronological score series
    """
    analyses = (
        db.query(Analysis)
        .join(Video, Analysis.video_id == Video.id)
        .filter(
            Video.user_id == user_id,
            Video.is_saved.is_(True),
            Analysis.status == AnalysisStatus.COMPLETED,
        )
        .order_by(Analysis.completed_at.asc(), Analysis.id.asc())
        .all()
    )

    analysis_ids = [analysis.id for analysis in analyses]
    top_errors: List[Dict[str, Any]] = []
    if analysis_ids:
        rows = (
            db.query(Error.error_type, func.count(Error.id))
            .filter(Error.analysis_id.in_(analysis_ids))
            .group_by(Error.error_type)
            .order_by(func.count(Error.id).desc(), Error.error_type.asc())
            .limit(3)
            .all()
        )
        top_errors = [
            {"error_type": error_type, "count": count}
            for error_type, count in rows
        ]

    progress: List[Dict[str, Any]] = []
    for analysis in analyses:
        completed_at: Optional[datetime] = analysis.completed_at or analysis.started_at
        progress.append({
            "analysis_id": analysis.id,
            "completed_at": completed_at,
            "overall_score": analysis.overall_score,
            "rhythm_score": analysis.rhythm_score,
            "posture_score": analysis.posture_score,
            "technique_score": analysis.technique_score,
            "music_score": analysis.music_score,
        })

    return {
        "saved_analyses": len(analyses),
        "average_scores": {
            "overall": _mean([item.overall_score for item in analyses]),
            "rhythm": _mean([item.rhythm_score for item in analyses]),
            "posture": _mean([item.posture_score for item in analyses]),
            "technique": _mean([item.technique_score for item in analyses]),
            "music": _mean([item.music_score for item in analyses]),
        },
        "top_errors": top_errors,
        "progress": progress,
    }
