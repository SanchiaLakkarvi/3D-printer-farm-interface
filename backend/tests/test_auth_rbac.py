"""HTTP tests for RBAC guards and protected probe endpoints (Fake Auth)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.auth.fake import FakeAuthAdapter
from app.models.enums import UserRole
from app.models.user import User

STUDENT_EMAIL = "22705555@student.uwa.edu.au"
STUDENT_PASSWORD = "secure-password-1"
FARMER_EMAIL = "farmer1@uwa.edu.au"
FARMER_PASSWORD = "farmer-password-1"
ADMIN_EMAIL = "christopher.lamb@uwa.edu.au"
ADMIN_PASSWORD = "admin-password-1"


def _seed_profile(
    *,
    db_session: Session,
    auth_adapter: FakeAuthAdapter,
    email: str,
    password: str,
    role: UserRole,
    first_name: str,
    last_name: str,
    student_number: str | None = None,
    department: str | None = None,
) -> User:
    user_id = auth_adapter.seed_user(email=email, password=password)
    user = User(
        id=user_id,
        email=email.lower(),
        first_name=first_name,
        last_name=last_name,
        student_number=student_number,
        role=role,
        department=department,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _seed_all_roles(
    db_session: Session,
    auth_adapter: FakeAuthAdapter,
) -> None:
    _seed_profile(
        db_session=db_session,
        auth_adapter=auth_adapter,
        email=STUDENT_EMAIL,
        password=STUDENT_PASSWORD,
        role=UserRole.STUDENT,
        first_name="Ada",
        last_name="Lovelace",
        student_number="22705555",
        department="engineering",
    )
    _seed_profile(
        db_session=db_session,
        auth_adapter=auth_adapter,
        email=FARMER_EMAIL,
        password=FARMER_PASSWORD,
        role=UserRole.FARMER,
        first_name="Fran",
        last_name="Farmer",
    )
    _seed_profile(
        db_session=db_session,
        auth_adapter=auth_adapter,
        email=ADMIN_EMAIL,
        password=ADMIN_PASSWORD,
        role=UserRole.ADMIN,
        first_name="Christopher",
        last_name="Lamb",
    )


def _token(auth_client: TestClient, email: str, password: str) -> str:
    response = auth_client.post(
        "/api/auth/signin",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_farmer_probe_allows_farmer_and_admin_rejects_student(
    auth_client: TestClient,
    db_session: Session,
    auth_adapter: FakeAuthAdapter,
) -> None:
    _seed_all_roles(db_session, auth_adapter)

    farmer = auth_client.get(
        "/api/rbac/farmer",
        headers={
            "Authorization": f"Bearer {_token(auth_client, FARMER_EMAIL, FARMER_PASSWORD)}"
        },
    )
    assert farmer.status_code == 200
    assert farmer.json()["ok"] is True
    assert farmer.json()["role"] == "farmer"

    admin = auth_client.get(
        "/api/rbac/farmer",
        headers={
            "Authorization": f"Bearer {_token(auth_client, ADMIN_EMAIL, ADMIN_PASSWORD)}"
        },
    )
    assert admin.status_code == 200
    assert admin.json()["role"] == "admin"

    student = auth_client.get(
        "/api/rbac/farmer",
        headers={
            "Authorization": (
                f"Bearer {_token(auth_client, STUDENT_EMAIL, STUDENT_PASSWORD)}"
            )
        },
    )
    assert student.status_code == 403
    assert student.json()["detail"]["code"] == "FORBIDDEN"


def test_admin_probe_allows_admin_rejects_farmer_and_student(
    auth_client: TestClient,
    db_session: Session,
    auth_adapter: FakeAuthAdapter,
) -> None:
    _seed_all_roles(db_session, auth_adapter)

    admin = auth_client.get(
        "/api/rbac/admin",
        headers={
            "Authorization": f"Bearer {_token(auth_client, ADMIN_EMAIL, ADMIN_PASSWORD)}"
        },
    )
    assert admin.status_code == 200
    assert admin.json()["ok"] is True
    assert admin.json()["role"] == "admin"

    farmer = auth_client.get(
        "/api/rbac/admin",
        headers={
            "Authorization": f"Bearer {_token(auth_client, FARMER_EMAIL, FARMER_PASSWORD)}"
        },
    )
    assert farmer.status_code == 403
    assert farmer.json()["detail"]["code"] == "FORBIDDEN"

    student = auth_client.get(
        "/api/rbac/admin",
        headers={
            "Authorization": (
                f"Bearer {_token(auth_client, STUDENT_EMAIL, STUDENT_PASSWORD)}"
            )
        },
    )
    assert student.status_code == 403
    assert student.json()["detail"]["code"] == "FORBIDDEN"


def test_submit_probe_allows_student_farmer_and_admin(
    auth_client: TestClient,
    db_session: Session,
    auth_adapter: FakeAuthAdapter,
) -> None:
    """Submit capability: Admin ⊃ Farmer ⊃ submit (student)."""
    _seed_all_roles(db_session, auth_adapter)

    for email, password, expected_role in (
        (STUDENT_EMAIL, STUDENT_PASSWORD, "student"),
        (FARMER_EMAIL, FARMER_PASSWORD, "farmer"),
        (ADMIN_EMAIL, ADMIN_PASSWORD, "admin"),
    ):
        response = auth_client.get(
            "/api/rbac/submit",
            headers={
                "Authorization": f"Bearer {_token(auth_client, email, password)}"
            },
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert response.json()["role"] == expected_role


def test_submit_probe_rejects_missing_token(auth_client: TestClient) -> None:
    response = auth_client.get("/api/rbac/submit")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "UNAUTHORIZED"


def test_client_supplied_role_query_cannot_escalate(
    auth_client: TestClient,
    db_session: Session,
    auth_adapter: FakeAuthAdapter,
) -> None:
    _seed_all_roles(db_session, auth_adapter)
    token = _token(auth_client, STUDENT_EMAIL, STUDENT_PASSWORD)

    response = auth_client.get(
        "/api/rbac/admin",
        params={"role": "admin"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"

    farmer_probe = auth_client.get(
        "/api/rbac/farmer",
        params={"role": "farmer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert farmer_probe.status_code == 403
    assert farmer_probe.json()["detail"]["code"] == "FORBIDDEN"


def test_client_supplied_role_body_cannot_escalate(
    auth_client: TestClient,
    db_session: Session,
    auth_adapter: FakeAuthAdapter,
) -> None:
    _seed_all_roles(db_session, auth_adapter)
    token = _token(auth_client, STUDENT_EMAIL, STUDENT_PASSWORD)

    response = auth_client.post(
        "/api/rbac/admin",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "admin"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"
