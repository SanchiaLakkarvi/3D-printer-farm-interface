"""Shared pytest fixtures: plain client + Fake Auth / disposable DB.

Extends the base conftest with multi-table support for printers and materials.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import JSON, create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.auth.fake import FakeAuthAdapter
from app.api.deps import get_auth_port
from app.db.base import Base
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


def _patch_for_sqlite() -> None:
    """Strip Postgres-only features so SQLite can create tables.

    - Replace JSONB columns with JSON.
    - Remove server_defaults that use Postgres syntax.
    """
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
            if column.server_default is not None:
                column.server_default = None


_patch_for_sqlite()


@pytest.fixture()
def db_session() -> Session:
    """In-memory SQLite session with all tables for API tests."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection, connection_record) -> None:
        del connection_record
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def auth_client(db_session: Session, auth_adapter: FakeAuthAdapter) -> TestClient:
    """TestClient with Fake Auth + full schema for API tests."""

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
