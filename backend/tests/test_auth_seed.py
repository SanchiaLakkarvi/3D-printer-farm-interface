"""HTTP tests for Seed Users (Fake Auth + in-memory DB)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.auth.fake import FakeAuthAdapter
from app.core.exceptions import BadRequestError, ConflictError
from app.models.enums import UserRole
from app.services import auth_service


@dataclass(frozen=True, slots=True)
class _SeedSettings:
    seed_admin_email: str = "christopher.lamb@uwa.edu.au"
    seed_admin_password: str = "admin-seed-password-1"
    seed_farmer1_email: str = "farmer1@uwa.edu.au"
    seed_farmer1_password: str = "farmer1-seed-password-1"
    seed_farmer2_email: str = "farmer2@uwa.edu.au"
    seed_farmer2_password: str = "farmer2-seed-password-1"
    seed_farmer3_email: str = "farmer3@uwa.edu.au"
    seed_farmer3_password: str = "farmer3-seed-password-1"


def test_seed_users_then_signin_returns_roles_and_null_student_number(
    auth_client: TestClient,
    db_session: Session,
    auth_adapter: FakeAuthAdapter,
) -> None:
    seeded = auth_service.seed_demo_users(
        db=db_session,
        auth=auth_adapter,
        settings=_SeedSettings(),
    )

    assert len(seeded) == 4
    by_email = {user.email: user for user in seeded}
    assert by_email["christopher.lamb@uwa.edu.au"].role == UserRole.ADMIN
    assert by_email["christopher.lamb@uwa.edu.au"].student_number is None
    assert by_email["christopher.lamb@uwa.edu.au"].first_name == "Christopher"
    assert by_email["christopher.lamb@uwa.edu.au"].last_name == "Lamb"
    for email in (
        "farmer1@uwa.edu.au",
        "farmer2@uwa.edu.au",
        "farmer3@uwa.edu.au",
    ):
        assert by_email[email].role == UserRole.FARMER
        assert by_email[email].student_number is None

    admin = auth_client.post(
        "/api/auth/signin",
        json={
            "email": "christopher.lamb@uwa.edu.au",
            "password": "admin-seed-password-1",
        },
    )
    assert admin.status_code == 200
    assert admin.json()["user"]["role"] == "admin"
    assert admin.json()["user"]["student_number"] is None
    assert admin.json()["user"]["id"] == str(
        by_email["christopher.lamb@uwa.edu.au"].id
    )
    assert "password" not in admin.json()
    assert "password" not in admin.json()["user"]

    for index, email in enumerate(
        ("farmer1@uwa.edu.au", "farmer2@uwa.edu.au", "farmer3@uwa.edu.au"),
        start=1,
    ):
        response = auth_client.post(
            "/api/auth/signin",
            json={"email": email, "password": f"farmer{index}-seed-password-1"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["user"]["role"] == "farmer"
        assert body["user"]["student_number"] is None
        assert body["user"]["id"] == str(by_email[email].id)


def test_seed_users_rejects_missing_passwords(
    db_session: Session,
    auth_adapter: FakeAuthAdapter,
) -> None:
    settings = _SeedSettings(seed_admin_password="")
    with pytest.raises(BadRequestError) as exc_info:
        auth_service.seed_demo_users(
            db=db_session,
            auth=auth_adapter,
            settings=settings,
        )
    assert exc_info.value.detail["code"] == "SEED_PASSWORD_REQUIRED"


def test_seed_users_rejects_duplicate_passwords(
    db_session: Session,
    auth_adapter: FakeAuthAdapter,
) -> None:
    settings = _SeedSettings(
        seed_admin_password="same-password",
        seed_farmer1_password="same-password",
        seed_farmer2_password="farmer2-seed-password-1",
        seed_farmer3_password="farmer3-seed-password-1",
    )
    with pytest.raises(BadRequestError) as exc_info:
        auth_service.seed_demo_users(
            db=db_session,
            auth=auth_adapter,
            settings=settings,
        )
    assert exc_info.value.detail["code"] == "SEED_PASSWORD_REQUIRED"


def test_seed_users_rejects_existing_email(
    db_session: Session,
    auth_adapter: FakeAuthAdapter,
) -> None:
    settings = _SeedSettings()
    auth_service.seed_demo_users(
        db=db_session,
        auth=auth_adapter,
        settings=settings,
    )
    with pytest.raises(ConflictError):
        auth_service.seed_demo_users(
            db=db_session,
            auth=auth_adapter,
            settings=settings,
        )
