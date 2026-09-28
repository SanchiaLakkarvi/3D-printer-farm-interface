"""Demo accounts: fake-auth logins that survive a backend restart."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.auth.fake import FakeAuthAdapter
from app.models.enums import UserRole
from app.models.user import User
from app.services.demo_accounts import DemoAccount, parse_demo_accounts, seed_demo_accounts


def test_parse_accounts_defaults_and_roles() -> None:
    parsed = parse_demo_accounts(
        " A@student.uwa.edu.au:pw-one , b@uwa.edu.au:pw-two:ADMIN,,c@uwa.edu.au:pw3:farmer"
    )
    assert parsed == [
        DemoAccount("a@student.uwa.edu.au", "pw-one", UserRole.STUDENT),
        DemoAccount("b@uwa.edu.au", "pw-two", UserRole.ADMIN),
        DemoAccount("c@uwa.edu.au", "pw3", UserRole.FARMER),
    ]
    assert parse_demo_accounts("") == []


@pytest.mark.parametrize("bad", ["just-an-email", "a@b.c:", ":pw", "a@b.c:pw:boss", "a:b:c:d"])
def test_parse_rejects_malformed_entries(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_demo_accounts(bad)


def test_seeded_accounts_can_sign_in_with_their_role(
    auth_client: TestClient, db_session: Session, auth_adapter: FakeAuthAdapter
) -> None:
    seed_demo_accounts(
        db_session,
        auth_adapter,
        parse_demo_accounts("00000001@student.uwa.edu.au:secret-1:admin,12345678@student.uwa.edu.au:secret-2"),
    )
    admin = auth_client.post("/api/auth/signin", json={"email": "00000001@student.uwa.edu.au", "password": "secret-1"})
    student = auth_client.post("/api/auth/signin", json={"email": "12345678@student.uwa.edu.au", "password": "secret-2"})
    assert admin.status_code == 200 and admin.json()["user"]["role"] == "admin"
    assert student.status_code == 200 and student.json()["user"]["role"] == "student"
    assert student.json()["user"]["student_number"] == "12345678"


def test_restart_keeps_existing_profile_and_its_id(db_session: Session) -> None:
    """Profile saved in Postgres, but the in-memory login is gone (fresh adapter)."""
    old_id = uuid.uuid4()
    db_session.add(
        User(id=old_id, email="12345678@student.uwa.edu.au", first_name="June", last_name="Real",
             student_number="12345678", role=UserRole.STUDENT, department="Engineering",
             created_at=datetime.now(timezone.utc))
    )
    db_session.commit()

    fresh = FakeAuthAdapter()
    seeded = seed_demo_accounts(
        db_session, fresh, [DemoAccount("12345678@student.uwa.edu.au", "new-password", UserRole.ADMIN)]
    )

    assert seeded == ["12345678@student.uwa.edu.au (admin)"]
    assert fresh.sign_in(email="12345678@student.uwa.edu.au", password="new-password").user_id == old_id
    users = db_session.scalars(select(User)).all()
    assert len(users) == 1  # no duplicate row, so job history stays attached
    assert users[0].role is UserRole.ADMIN and users[0].first_name == "June"  # role updated, name kept
    assert users[0].department == "Engineering"


def test_seeding_twice_is_harmless(db_session: Session, auth_adapter: FakeAuthAdapter) -> None:
    accounts = [DemoAccount("x@uwa.edu.au", "pw-pw-pw", UserRole.FARMER)]
    assert seed_demo_accounts(db_session, auth_adapter, accounts) == ["x@uwa.edu.au (farmer)"]
    assert seed_demo_accounts(db_session, auth_adapter, accounts) == []
    user = db_session.scalars(select(User)).one()
    assert user.role is UserRole.FARMER and user.student_number is None  # non-student email


def test_farmer_with_a_staff_email_can_sign_in(
    auth_client: TestClient, db_session: Session, auth_adapter: FakeAuthAdapter
) -> None:
    seed_demo_accounts(
        db_session, auth_adapter, parse_demo_accounts("farmer.demo@uwa.edu.au:secret-3:farmer")
    )
    resp = auth_client.post("/api/auth/signin", json={"email": "farmer.demo@uwa.edu.au", "password": "secret-3"})
    assert resp.status_code == 200
    assert resp.json()["user"]["role"] == "farmer"
    assert resp.json()["user"]["student_number"] is None
