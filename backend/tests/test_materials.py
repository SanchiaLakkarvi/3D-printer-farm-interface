"""HTTP tests for Material API endpoints (Fake Auth + in-memory DB)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.auth.fake import FakeAuthAdapter
from app.models.enums import UserRole
from app.models.user import User

STUDENT_EMAIL = "22705555@student.uwa.edu.au"
STUDENT_PASSWORD = "secure-password-1"
ADMIN_EMAIL = "christopher.lamb@uwa.edu.au"
ADMIN_PASSWORD = "admin-password-1"


def _seed_profile(
    *,
    db_session: Session,
    auth_adapter: FakeAuthAdapter,
    email: str,
    password: str,
    role: UserRole,
) -> None:
    user_id = auth_adapter.seed_user(email=email, password=password)
    user = User(
        id=user_id,
        email=email.lower(),
        first_name="Test",
        last_name="User",
        student_number=None,
        role=role,
        department=None,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    db_session.commit()


def _seed_users(db_session: Session, auth_adapter: FakeAuthAdapter) -> None:
    _seed_profile(
        db_session=db_session,
        auth_adapter=auth_adapter,
        email=STUDENT_EMAIL,
        password=STUDENT_PASSWORD,
        role=UserRole.STUDENT,
    )
    _seed_profile(
        db_session=db_session,
        auth_adapter=auth_adapter,
        email=ADMIN_EMAIL,
        password=ADMIN_PASSWORD,
        role=UserRole.ADMIN,
    )


def _token(auth_client: TestClient, email: str, password: str) -> str:
    response = auth_client.post(
        "/api/auth/signin",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_list_materials_unauthenticated(auth_client: TestClient) -> None:
    response = auth_client.get("/api/materials")
    assert response.status_code == 401


def test_list_materials_empty(
    auth_client: TestClient, db_session: Session, auth_adapter: FakeAuthAdapter,
) -> None:
    _seed_users(db_session, auth_adapter)
    token = _token(auth_client, STUDENT_EMAIL, STUDENT_PASSWORD)

    response = auth_client.get(
        "/api/materials",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_create_material_as_admin(
    auth_client: TestClient, db_session: Session, auth_adapter: FakeAuthAdapter,
) -> None:
    _seed_users(db_session, auth_adapter)
    token = _token(auth_client, ADMIN_EMAIL, ADMIN_PASSWORD)

    response = auth_client.post(
        "/api/materials",
        json={"name": "PLA Black", "type": "PLA", "colour": "black"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "PLA Black"
    assert data["type"] == "PLA"
    assert data["colour"] == "black"
    assert "id" in data


def test_create_material_as_student_forbidden(
    auth_client: TestClient, db_session: Session, auth_adapter: FakeAuthAdapter,
) -> None:
    _seed_users(db_session, auth_adapter)
    token = _token(auth_client, STUDENT_EMAIL, STUDENT_PASSWORD)

    response = auth_client.post(
        "/api/materials",
        json={"name": "PLA White", "type": "PLA", "colour": "white"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"


def test_list_materials_returns_created(
    auth_client: TestClient, db_session: Session, auth_adapter: FakeAuthAdapter,
) -> None:
    _seed_users(db_session, auth_adapter)
    admin_token = _token(auth_client, ADMIN_EMAIL, ADMIN_PASSWORD)
    student_token = _token(auth_client, STUDENT_EMAIL, STUDENT_PASSWORD)

    # Admin creates a material.
    auth_client.post(
        "/api/materials",
        json={"name": "PETG Blue", "type": "PETG", "colour": "blue"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Student can list it.
    response = auth_client.get(
        "/api/materials",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    materials = response.json()
    assert len(materials) == 1
    assert materials[0]["name"] == "PETG Blue"
