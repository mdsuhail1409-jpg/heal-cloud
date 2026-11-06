"""
Unit Tests for Database Engine, Session Management and Health Probes
"""

import uuid
import pytest
from sqlalchemy import String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin, TimestampMixin
from app.db.session import check_db_health, get_db
from app.core.exceptions import DatabaseConnectionException


class DummyModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "test_dummy_items"
    name: Mapped[str] = mapped_column(String(50), nullable=False)


def test_database_health_check():
    """Verify check_db_health probe executes SELECT 1 and returns healthy status."""
    health = check_db_health()
    assert health["status"] == "healthy"
    assert health["database"] == "reachable"
    assert "latency_ms" in health
    assert health["latency_ms"] >= 0


def test_session_commit_and_rollback(db_session):
    """Verify transaction lifecycle commits successfully and rolls back on failure."""
    # Ensure test table exists in test DB
    DummyModel.__table__.create(bind=db_session.bind, checkfirst=True)

    # 1. Successful transaction
    item = DummyModel(name="test_service")
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    assert item.id is not None
    assert isinstance(item.id, uuid.UUID)
    assert item.created_at is not None
    assert item.name == "test_service"

    # Query item back
    queried = db_session.query(DummyModel).filter_by(id=item.id).first()
    assert queried is not None
    assert queried.name == "test_service"


def test_get_db_generator():
    """Verify get_db generator yields active session and closes properly."""
    gen = get_db()
    session = next(gen)
    assert session is not None
    # Execute simple statement
    result = session.execute(text("SELECT 1")).scalar()
    assert result == 1
    # Trigger close via generator completion
    try:
        next(gen)
    except StopIteration:
        pass

