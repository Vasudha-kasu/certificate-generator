import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.services import processor


@pytest.fixture()
def session_factory(tmp_path):
    """A brand-new empty database for every single test."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    yield factory
    engine.dispose()


@pytest.fixture()
def client(session_factory, tmp_path, monkeypatch):
    """A fake browser wired to the test database and a temp output folder."""

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    # Requests use the test database...
    app.dependency_overrides[get_db] = override_get_db
    # ...and so does the background processor, which opens its own session.
    monkeypatch.setattr(processor, "SessionLocal", session_factory)
    # PDFs go to a temp folder, not your real generated/ folder.
    monkeypatch.setattr(processor, "OUTPUT_DIR", str(tmp_path / "generated"))

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()