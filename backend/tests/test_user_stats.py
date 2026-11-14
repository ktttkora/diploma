"""
Tests for profile statistics and the display name update.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  -- register every table on Base.metadata
from app.api.deps import get_current_user
from app.db.session import Base, get_db
from app.main import app
from app.models.analysis import Analysis, AnalysisStatus
from app.models.error import Error, ErrorSeverity
from app.models.user import User
from app.models.video import Video
from app.services.stats_service import build_user_stats


@pytest.fixture
def db():
    """In-memory database with the application schema."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()


def _user(db, email: str, name: str | None = None) -> User:
    user = User(email=email, hashed_password="hashed", display_name=name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _saved_analysis(
    db,
    user: User,
    *,
    filename: str,
    overall: float,
    rhythm: float | None,
    posture: float | None,
    completed_at: datetime,
    errors: list[tuple[str, str | None]],
) -> Analysis:
    video = Video(
        user_id=user.id,
        filename=filename,
        file_path=f"/tmp/{user.id}-{filename}",
        file_size=1000,
        duration=30.0,
        fps=30.0,
        is_saved=True,
        saved_at=completed_at,
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    analysis = Analysis(
        video_id=video.id,
        status=AnalysisStatus.COMPLETED,
        overall_score=overall,
        rhythm_score=rhythm,
        posture_score=posture,
        technique_score=70.0,
        music_score=None,
        total_errors=len(errors),
        started_at=completed_at,
        completed_at=completed_at,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    for index, (error_type, screenshot) in enumerate(errors):
        db.add(Error(
            analysis_id=analysis.id,
            element_name="Американка",
            timestamp=float(index),
            error_type=error_type,
            severity=ErrorSeverity.MEDIUM,
            description="Описание",
            screenshot_path=screenshot,
        ))
    db.commit()
    return analysis


def test_stats_average_top_errors_and_ignore_other_users(db) -> None:
    owner = _user(db, "owner@example.com", "Анна")
    other = _user(db, "other@example.com")
    start = datetime(2026, 10, 1, tzinfo=timezone.utc)

    _saved_analysis(
        db, owner,
        filename="first.mp4",
        overall=60,
        rhythm=50,
        posture=None,
        completed_at=start,
        errors=[("rhythm", "/shots/1.jpg"), ("rhythm", None), ("posture", None)],
    )
    _saved_analysis(
        db, owner,
        filename="second.mp4",
        overall=80,
        rhythm=90,
        posture=70,
        completed_at=start + timedelta(days=1),
        errors=[("technique", "/shots/2.jpg")],
    )
    _saved_analysis(
        db, other,
        filename="theirs.mp4",
        overall=10,
        rhythm=10,
        posture=10,
        completed_at=start,
        errors=[("rhythm", None)],
    )

    stats = build_user_stats(db, owner.id)

    assert stats["saved_analyses"] == 2
    assert stats["average_scores"]["overall"] == 70.0
    assert stats["average_scores"]["rhythm"] == 70.0
    # The missing posture on the first analysis is left out of the mean
    assert stats["average_scores"]["posture"] == 70.0
    assert stats["average_scores"]["music"] is None
    assert stats["top_errors"][0] == {"error_type": "rhythm", "count": 2}
    assert [point["overall_score"] for point in stats["progress"]] == [60, 80]


def test_stats_endpoint_and_display_name(db) -> None:
    user = _user(db, "dancer@example.com")

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        client = TestClient(app)

        empty = client.get("/api/users/stats")
        assert empty.status_code == 200
        assert empty.json()["saved_analyses"] == 0
        assert empty.json()["top_errors"] == []

        renamed = client.put("/api/users/me", json={"display_name": "  Катя  "})
        assert renamed.status_code == 200
        assert renamed.json()["display_name"] == "Катя"

        cleared = client.put("/api/users/me", json={"display_name": "   "})
        assert cleared.status_code == 200
        assert cleared.json()["display_name"] is None
    finally:
        app.dependency_overrides.clear()
