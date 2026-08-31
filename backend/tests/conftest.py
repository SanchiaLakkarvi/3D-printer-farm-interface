"""Shared pytest fixtures: plain client + Fake Auth / disposable users DB."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.auth.fake import FakeAuthAdapter
from app.api.deps import get_auth_port
from app.db.session import get_db
from app.main import app
from app.models.user import User


@pytest.fixture()
def client() -> TestClient:
    """Synchronous test client without DB/Auth overrides."""
    return TestClient(app)


@pytest.fixture()
def auth_adapter() -> FakeAuthAdapter:
    return FakeAuthAdapter()


@pytest.fixture()
def db_session() -> Session:
    """SQLite session with only the users table (auth HTTP tests)."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
        del connection_record
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    table = User.__table__
    saved_defaults = [(column, column.server_default) for column in table.columns]
    for column, _ in saved_defaults:
        column.server_default = None
    try:
        table.create(bind=engine)
    finally:
        for column, default in saved_defaults:
            column.server_default = default

    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        table.drop(bind=engine)
        engine.dispose()


@pytest.fixture()
def auth_client(db_session: Session, auth_adapter: FakeAuthAdapter) -> TestClient:
    """TestClient with Fake Auth + users table for /api/auth tests."""

    def _override_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_auth_port] = lambda: auth_adapter
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
