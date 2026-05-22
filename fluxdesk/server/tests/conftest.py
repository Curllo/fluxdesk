import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure server modules are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("FLUXDESK_PORT", "9999")
os.environ.setdefault("FLUXDESK_API_TOKEN", "test-token")
os.environ.setdefault("FLUXDESK_INTERNAL_TOKEN", "test-internal")
os.environ.setdefault("FLUXDESK_DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture(scope="session")
def db_engine():
    """Create a fresh in-memory database engine for tests."""
    from sqlalchemy import create_engine
    from models.database import Base
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    """Provide a transactional database session for each test."""
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """Provide a FastAPI test client."""
    from main import app
    return TestClient(app)
