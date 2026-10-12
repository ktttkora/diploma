"""
Database session management module.

Provides sync SQLAlchemy engine, session factory, and FastAPI dependency
for database access. Uses psycopg (v3) driver.
Lazy engine creation to avoid import-time DB connection.
"""

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator, Optional

from app.config import settings


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_engine() -> Engine:
    """
    Get or create SQLAlchemy engine (lazy).

    Returns:
        SQLAlchemy Engine instance
    """
    global _engine
    if _engine is None:
        # Use psycopg (v3) driver explicitly
        db_url = settings.DATABASE_URL
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
        _engine = create_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )
    return _engine


def get_session_factory() -> sessionmaker:
    """
    Get or create session factory (lazy).

    Returns:
        SQLAlchemy sessionmaker instance
    """
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            class_=Session,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
    return _SessionLocal


# Backwards compat: SessionLocal used by tasks
def _get_session_local() -> sessionmaker:
    return get_session_factory()


class _SessionLocalProxy:
    """Lazy proxy for SessionLocal to avoid import-time engine creation."""

    def __call__(self, *args, **kwargs):
        return get_session_factory()(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(get_session_factory(), name)


SessionLocal = _SessionLocalProxy()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Yields:
        Session: Database session

    Example:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = get_session_factory()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
