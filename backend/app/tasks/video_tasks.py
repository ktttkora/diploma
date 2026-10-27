"""
Main video processing pipeline (Celery task).

Steps: local rhythm analysis, key-frame extraction, AI analysis,
error merging, top-10 selection, screenshot generation, DB persistence.
"""

from celery import shared_task
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import json
import tempfile
import time

from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.video import Video
from app.models.analysis import Analysis, AnalysisStatus
from app.models.error import Error, ErrorSeverity


SEVERITY_MAP = {
    "low": ErrorSeverity.LOW,
    "medium": ErrorSeverity.MEDIUM,
    "high": ErrorSeverity.HIGH,
    "critical": ErrorSeverity.CRITICAL
}

# Sort order for picking the top errors: most severe first
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

MAX_ERRORS = 10
AI_FRAME_COUNT = 20

# Errors of one category closer than this (seconds) describe the same moment
DUPLICATE_WINDOW = 0.25


def _set_progress(task, step: int, total: int, message: str) -> None:
    """
    Report progress through Celery's result backend.

    Args:
        task: Bound Celery task
        step: Current step number (1-indexed)
        total: Total number of steps
        message: Human-readable stage description
    """
    try:
        task.update_state(
            state="PROGRESS",
            meta={"step": step, "total": total, "message": message}
        )
    except Exception:
        pass  # Progress reporting is best-effort


def _merge_errors(
    rhythm_errors: List[Dict[str, Any]],
    ai_errors: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Merge rhythm and AI errors, then keep the most severe ones.

    Args:
        rhythm_errors: Errors from local rhythm analysis
        ai_errors: Errors from AI analysis

    Returns:
        Up to MAX_ERRORS errors, sorted by severity then timestamp
    """
    merged: List[Dict[str, Any]] = []

    for err in rhythm_errors:
        merged.append({
            "timestamp": float(err.get("timestamp", 0)),
            "category": "rhythm",
            "severity": err.get("severity", "medium"),
            "title": err.get("title", "Ошибка ритма"),
            "description": err.get("description", ""),
            "recommendation": err.get("recommendation", ""),
            "detected_element": err.get("detected_element"),
        })

    for err in ai_errors:
        merged.append({
            "timestamp": float(err.get("timestamp", 0)),
            "category": err.get("category", "technique"),
            "severity": err.get("severity", "medium"),
            "title": err.get("title", "Ошибка техники"),
            "description": err.get("description", ""),
            "recommendation": err.get("recommendation", ""),
            "detected_element": err.get("detected_element"),
        })

    merged.sort(key=lambda e: (
        SEVERITY_ORDER.get(e["severity"], 2),
        e["timestamp"]
    ))

    # Drop near-duplicates: the same kind of error reported again within
    # DUPLICATE_WINDOW seconds. The more severe one wins, since it sorts first.
    unique: List[Dict[str, Any]] = []
    for err in merged:
        is_duplicate = any(
            kept["category"] == err["category"]
            and abs(kept["timestamp"] - err["timestamp"]) < DUPLICATE_WINDOW
            for kept in unique
        )
        if not is_duplicate:
            unique.append(err)

    return unique[:MAX_ERRORS]


def _average(*values: Optional[float]) -> Optional[float]:
    """
    Average the values that are present.

    Args:
        *values: Scores, or None for a skipped category

    Returns:
        Mean of the non-None values, or None if there are none
    """
    present = [v for v in values if v is not None]
    if not present:
        return None
    return round(sum(present) / len(present), 1)


@celery_app.task(name="app.tasks.video_tasks.process_video_task", bind=True)
def process_video_task(self, video_id: int, analysis_id: int) -> Dict[str, Any]:
    """
    Run the full analysis pipeline for one video.

    Args:
        video_id: Video to process
        analysis_id: Analysis row to update

    Returns:
        Summary of the run

    Raises:
        Exception: Re-raised after marking the analysis FAILED
    """
    db = SessionLocal()
    started = time.monotonic()

    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()

        if not video or not analysis:
            return {"status": "failed", "error": "Video or analysis not found"}

        analysis.status = AnalysisStatus.PROCESSING
        analysis.error_message = None
        db.commit()

        # Step 1: local rhythm analysis (MediaPipe + librosa)
        _set_progress(self, 1, 4, "Анализ ритма")
        from app.services.rhythm_service import rhythm_service
        rhythm_result = rhythm_service.analyze_rhythm(video.file_path)
        rhythm_errors = rhythm_result.get("errors", [])
        rhythm_score = rhythm_result.get("rhythm_score")

        # Step 2: extract key frames for AI analysis
        _set_progress(self, 2, 4, "Извлечение кадров")
        ai_result: Dict[str, Any] = {}
        ai_error: Optional[str] = None

        from app.services.claude_service import (
            get_ai_service,
            ClaudeUnavailableError
        )
        claude = get_ai_service()

        if claude.is_configured:
            from app.utils.frame_extractor import extract_key_frames
            with tempfile.TemporaryDirectory() as frames_dir:
                frame_paths = extract_key_frames(
                    video.file_path, frames_dir, count=AI_FRAME_COUNT
                )

                # Step 3: AI analysis of posture, technique, musicality
                _set_progress(self, 3, 4, "AI-анализ")
                try:
                    ai_result = claude.analyze_video(
                        frame_paths,
                        rhythm_errors,
                        tempo=rhythm_result.get("tempo"),
                        user_poses=rhythm_result.get("poses"),
                        user_aspect=rhythm_result.get("video_aspect"),
                        duration=video.duration
                    )
                except (ClaudeUnavailableError, RuntimeError) as exc:
                    # Rhythm results are still useful, so record the AI
                    # failure and finish with a partial analysis
                    ai_error = str(exc)
        else:
            ai_error = (
                "AI-анализ пропущен: AI-провайдер не настроен или недоступен. "
                "Оценки постуры, техники и музыкальности недоступны."
            )

        # Step 4: merge errors, generate screenshots, persist results
        _set_progress(self, 4, 4, "Генерация скриншотов")

        from app.services.visualization_service import visualization_service

        top_errors = _merge_errors(rhythm_errors, ai_result.get("errors", []))

        for err in top_errors:
            error_record = Error(
                analysis_id=analysis_id,
                element_name=err.get("detected_element") or "не определён",
                timestamp=err["timestamp"],
                error_type=err["category"],
                severity=SEVERITY_MAP.get(err["severity"], ErrorSeverity.MEDIUM),
                description=f"{err['title']}. {err['description']}".strip(),
                screenshot_path=None
            )
            db.add(error_record)
            db.flush()

            # Screenshots are required for the results page, but a rendering
            # failure should not lose the error itself
            try:
                screenshot_path = visualization_service.create_error_screenshot(
                    video.file_path,
                    err["timestamp"],
                    {
                        "title": err["title"],
                        "recommendation": err["recommendation"],
                        "analysis_id": analysis_id,
                        "error_id": error_record.id
                    },
                    detected_element=err.get("detected_element")
                )
                error_record.screenshot_path = screenshot_path
            except Exception as exc:
                error_record.description += f" [скриншот недоступен: {exc}]"

        posture_score = ai_result.get("posture_score")
        technique_score = ai_result.get("technique_score")
        music_score = ai_result.get("musicality_score")

        analysis.rhythm_score = rhythm_score
        analysis.posture_score = posture_score
        analysis.technique_score = technique_score
        analysis.music_score = music_score
        analysis.overall_score = _average(
            rhythm_score, posture_score, technique_score, music_score
        )
        analysis.total_errors = len(top_errors)
        analysis.processing_time = round(time.monotonic() - started, 2)
        analysis.ai_response = json.dumps(ai_result, ensure_ascii=False) if ai_result else None
        analysis.error_message = ai_error
        analysis.status = AnalysisStatus.COMPLETED
        analysis.completed_at = datetime.utcnow()
        db.commit()

        return {
            "status": "completed",
            "analysis_id": analysis_id,
            "video_id": video_id,
            "overall_score": analysis.overall_score,
            "total_errors": len(top_errors),
            "ai_analyzed": bool(ai_result)
        }

    except Exception as exc:
        db.rollback()
        try:
            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            if analysis:
                analysis.status = AnalysisStatus.FAILED
                analysis.error_message = str(exc)
                analysis.processing_time = round(time.monotonic() - started, 2)
                analysis.completed_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()
