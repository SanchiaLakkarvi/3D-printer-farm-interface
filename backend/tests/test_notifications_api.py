"""HTTP tests for the notifications API: listing, unread count, read state and ownership."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.auth.fake import FakeAuthAdapter
from app.models.enums import NotificationType, UserRole
from app.models.notification import Notification
from app.models.user import User
from tests.test_jobs_reports import (
    FARMER_EMAIL,
    FARMER_PASSWORD,
    STUDENT_EMAIL,
    STUDENT_PASSWORD,
    _seed_profile,
    _token,
)

NOW = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)


def _add(db: Session, user: User, message: str, minutes_ago: int, is_read: bool = False) -> Notification:
    n = Notification(
        id=uuid.uuid4(), user_id=user.id, job_id=None, type=NotificationType.JOB_STARTED,
        message=message, is_read=is_read, sent_at=NOW - timedelta(minutes=minutes_ago),
    )
    db.add(n)
    db.commit()
    return n


@pytest.fixture()
def people(auth_client: TestClient, db_session: Session, auth_adapter: FakeAuthAdapter):
    student = _seed_profile(
        db_session=db_session, auth_adapter=auth_adapter, email=STUDENT_EMAIL,
        password=STUDENT_PASSWORD, role=UserRole.STUDENT,
    )
    farmer = _seed_profile(
        db_session=db_session, auth_adapter=auth_adapter, email=FARMER_EMAIL,
        password=FARMER_PASSWORD, role=UserRole.FARMER,
    )
    headers = {"Authorization": f"Bearer {_token(auth_client, STUDENT_EMAIL, STUDENT_PASSWORD)}"}
    return student, farmer, headers


def test_lists_only_own_notifications_newest_first(auth_client: TestClient, db_session: Session, people) -> None:
    student, farmer, headers = people
    _add(db_session, student, "older", minutes_ago=10)
    _add(db_session, student, "newer", minutes_ago=1)
    _add(db_session, farmer, "farmer's", minutes_ago=5)

    response = auth_client.get("/api/notifications", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert [n["message"] for n in body] == ["newer", "older"]
    assert set(body[0]) == {"id", "job_id", "type", "message", "is_read", "sent_at"}
    assert body[0]["type"] == "job_started" and body[0]["is_read"] is False


def test_unread_filter_limit_and_count(auth_client: TestClient, db_session: Session, people) -> None:
    student, _, headers = people
    _add(db_session, student, "read", minutes_ago=3, is_read=True)
    _add(db_session, student, "unread 1", minutes_ago=2)
    _add(db_session, student, "unread 2", minutes_ago=1)

    unread = auth_client.get("/api/notifications?unread=true", headers=headers).json()
    assert [n["message"] for n in unread] == ["unread 2", "unread 1"]
    assert len(auth_client.get("/api/notifications?limit=1", headers=headers).json()) == 1
    assert auth_client.get("/api/notifications/unread-count", headers=headers).json() == {"count": 2}


def test_mark_one_read(auth_client: TestClient, db_session: Session, people) -> None:
    student, _, headers = people
    n = _add(db_session, student, "hello", minutes_ago=1)

    response = auth_client.patch(f"/api/notifications/{n.id}/read", headers=headers)

    assert response.status_code == 200 and response.json()["is_read"] is True
    assert auth_client.get("/api/notifications/unread-count", headers=headers).json() == {"count": 0}


def test_cannot_read_someone_elses_notification(auth_client: TestClient, db_session: Session, people) -> None:
    _, farmer, headers = people
    theirs = _add(db_session, farmer, "farmer's", minutes_ago=1)

    response = auth_client.patch(f"/api/notifications/{theirs.id}/read", headers=headers)

    assert response.status_code == 404
    db_session.refresh(theirs)
    assert theirs.is_read is False


def test_unknown_notification_is_404(auth_client: TestClient, people) -> None:
    _, _, headers = people
    assert auth_client.patch(f"/api/notifications/{uuid.uuid4()}/read", headers=headers).status_code == 404


def test_mark_all_read_only_touches_own(auth_client: TestClient, db_session: Session, people) -> None:
    student, farmer, headers = people
    _add(db_session, student, "a", minutes_ago=2)
    _add(db_session, student, "b", minutes_ago=1)
    theirs = _add(db_session, farmer, "farmer's", minutes_ago=1)

    response = auth_client.post("/api/notifications/read-all", headers=headers)

    assert response.status_code == 200 and response.json() == {"count": 0}
    assert auth_client.get("/api/notifications/unread-count", headers=headers).json() == {"count": 0}
    db_session.refresh(theirs)
    assert theirs.is_read is False


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/notifications"),
        ("get", "/api/notifications/unread-count"),
        ("post", "/api/notifications/read-all"),
        ("patch", f"/api/notifications/{uuid.uuid4()}/read"),
    ],
)
def test_requires_sign_in(auth_client: TestClient, method: str, path: str) -> None:
    assert getattr(auth_client, method)(path).status_code == 401
