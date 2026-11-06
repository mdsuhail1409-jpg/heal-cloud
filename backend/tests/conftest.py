"""
Pytest Fixtures and Test Environment Setup
"""

import os
import pytest
from typing import Generator
from fastapi.testclient import TestClient

# Ensure test environment variables before importing app
TEST_DB_FILE = "./test_healcloud_suite.db"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_FILE}"
os.environ["DEBUG"] = "true"

from app.core.config import settings
from app.db.base import Base
import app.models  # Register all models in Base.metadata
from app.db.session import engine, SessionLocal, get_db
from app.main import create_application


@pytest.fixture(scope="session", autouse=True)
def clean_test_db_file():
    """Ensure clean database file before and after test session."""
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass
    yield
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass


@pytest.fixture(autouse=True)
def reset_db_per_test():
    """Drop and recreate all tables for clean isolation between tests."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator:
    """Provide a transactional database session for unit tests."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """TestClient using the test database configuration."""
    app = create_application()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
