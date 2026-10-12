"""
Updated video processing task with full pipeline integration.

Integrates: RhythmService -> ClaudeService -> VisualizationService -> DB save
"""

from celery import shared_task
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
import tempfile
import os

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


@celery_app.task(name="app.tasks.video_tasks.process_video_task", bind=True)
def process_video_task(self, video_id: int, analysis_id: int) -> Dict[str, Any]:
    """
    Full video processing pipeline.

    Steps:
    1. Rhythm analysis (local: MediaPipe + librosa)
    2. Extract key frames for Claude
    3. Claude API analysis (posture/technique/musicality)
    4. Merge all errors, take top-10 by severity
    5. Generate screenshots for each error
    6. Calculate scores, save to DB

    Args:
        video_id: Video ID to process
        analysis_id: Analysis ID to update

    Returns:
        Dict with processing results
    """
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()

        if not video or not analysis:
            return {"status": "failed", "error": "Video or analysis not found"}

        analysis.status = AnalysisStatus.PROCESSING
        db.commit()

        # STEP 1: Local rhythm analysis
        self.update_state(state="PROGRESS", meta={"step": 1, "total": 4, "message": "Analyzing rhythm..."})
        from app.services.rhythm_service import rhythm_service
        rhythm_result = rhythm_service.analyze_rhythm(video.file_path)
        rhythm_errors = rhythm_result.get("errors", [])

        # STEP 2: Extract key frames for Claude (evenly spaced, max 20)
        self.update_state(state="PROGRESS", meta={"step": 2, "total": 4, "message": "Extracting frames..."})
        from app.utils.video_utils import get_video_info
        video_info = get_video_info(video.file_path)
        duration = video_info.get("duration", 60)

        num_frames = min(20, max(5, int(duration / 10)))
        timestamps = [duration * (i + 1) / (num_frames + 1) for i in range(num_frames)]

        from app.utils.video_utils import extract_frames_batch
        with tempfile.TemporaryDirectory() as tmpdir:
            frame_paths = extract_frames_batch(video.file_path, timestamps, tmpdir)

            # STEP 3: Claude API analysis
            self.update_state(state="PROGRESS", meta={"step": 3, "total": 4, "message": "AI analysis..."})
            from app.services.claude_service import get_claude_service
            claude_service = get_claude_service()
            claude_result = claude_service.analyze_video(
                frame_paths,
                rhythm_errors,
                tempo=rhythm_result.get("tempo")
            )

        # STEP 4: Merge errors and take top-10
        self.update_state(state="PROGRESS", meta={"step": 4, "total": 4, "message": "Generating screenshots..."})
        all_errors = []

        # Add rhythm errors
        for err in rhythm_errors:
            all_errors.append({
                "timestamp": err["timestamp"],
                "category": "rhythm",
                "severity": err.get("severity", "medium"),
                "title": err.get("title", "Rhythm error"),
                "description": err.get("description", ""),
                "recommendation": err.get("recommendation", ""),
                "detected_element": err.get("detected_element")
            })

        # Add Claude errors
        for err in claude_result.get("errors", []):
            all_errors.append({
                "timestamp": err.get("timestamp", 0),
                "category": err.get("category", "technique"),
                "severity": err.get("severity", "medium"),
                "title": err.get("title", ""),
                "description": err.get("description", ""),
                "recommendation": err.get("recommendation", ""),
                "detected_element": err.get("detected_element")
            })

        # Sort by severity (critical > high > medium > low)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_errors.sort(key=lambda e: (severity_order.get(e["severity"], 2), e["timestamp"]))
        top_errors = all_errors[:10]

        # STEP 5: Generate screenshots and save errors
        from app.services.visualization_service import visualization_service

        saved_errors = []
        for i, err in enumerate(top_errors):
            error_record = Error(
                analysis_id=analysis_id,
                element_name=err.get("detected_element") or "unknown",
                timestamp=err["timestamp"],
                error_type=err["category"],
                severity=SEVERITY_MAP.get(err["severity"], ErrorSeverity.MEDIUM),
                description=f"{err['title']}: {err['description']}",
                screenshot_path=None  # Updated after generation
            )
            db.add(error_record)
            db.flush()  # Get error ID

            # Generate screenshot
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
            except Exception as e:
                # Screenshot failed, keep error without screenshot
                error_record.description += f" [screenshot failed: {e}]"

            saved_errors.append(error_record)

        # STEP 6: Calculate scores and finalize
        posture_score = claude_result.get("posture_score", 0)
        technique_score = claude_result.get("technique_score", 0)
        musicality_score = claude_result.get("musicality_score", 0)
        rhythm_score = rhythm_result.get("rhythm_score", 0)

        overall = round((posture_score + technique_score + musicality_score + rhythm_score) / 4, 1)

        analysis.overall_score = overall
        analysis.music_score = musicality_score
        analysis.rhythm_score = rhythm_score
        analysis.status = AnalysisStatus.COMPLETED
        analysis.completed_at = datetime.utcnow()
        db.commit()

        return {
            "status": "completed",
            "analysis_id": analysis_id,
            "video_id": video_id,
            "overall_score": overall,
            "total_errors": len(saved_errors)
        }

    except Exception as e:
        try:
            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            if analysis:
                analysis.status = AnalysisStatus.FAILED
                db.commit()
        except Exception:
            pass
        # Re-raise so Celery marks task as failed
        raise
    finally:
        db.close()
