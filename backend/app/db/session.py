"""
Database Engine, Session Management and Health Verification
"""

from typing import Generator
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import DatabaseConnectionException


def build_engine():
    """Build SQLAlchemy engine tailored for SQLite (development) or PostgreSQL (production)."""
    if settings.is_sqlite:
        return create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=NullPool,
            echo=settings.DEBUG,
        )
    else:
        return create_engine(
            settings.DATABASE_URL,
            poolclass=QueuePool,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_timeout=settings.DATABASE_POOL_TIMEOUT,
            pool_pre_ping=True,
            echo=settings.DEBUG,
        )


engine = build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a transactional database session.
    Commits changes automatically upon successful execution, rolls back on error.
    """
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(f"Database transaction rolled back due to error: {exc}")
        raise
    finally:
        db.close()


def check_db_health() -> dict:
    """
    Executes a lightweight query (SELECT 1) to verify database responsiveness.
    Returns status and round-trip latency in milliseconds.
    """
    start_time = time.perf_counter()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "healthy",
            "database": "reachable",
            "latency_ms": latency_ms,
        }
    except Exception as exc:
        logger.error(f"Database readiness probe failed: {exc}")
        raise DatabaseConnectionException(f"Database probe failed: {str(exc)}")
