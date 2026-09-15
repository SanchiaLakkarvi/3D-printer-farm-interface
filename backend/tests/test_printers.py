"""HTTP tests for Printer API endpoints (Fake Auth + in-memory DB)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.auth.fake import FakeAuthAdapter
from app.models.enums import UserRole
from app.models.material import Material
from app.models.user import User

STUDENT_EMAIL = "22706666@student.uwa.edu.au"
STUDENT_PASSWORD = "secure-password-2"
ADMIN_EMAIL = "admin.printer@uwa.edu.au"
ADMIN_PASSWORD = "admin-password-2"


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


def _create_material(db_session: Session) -> Material:
    material = Material(
        id=uuid.uuid4(), name="PLA Black", type="PLA", colour="black",
    )
    db_session.add(material)
    db_session.commit()
    db_session.refresh(material)
    return material


def test_list_printers_unauthenticated(auth_client: TestClient) -> None:
    response = auth_client.get("/api/printers")
    assert response.status_code == 401


def test_list_printers_empty(
    auth_client: TestClient, db_session: Session, auth_adapter: FakeAuthAdapter,
) -> None:
    _seed_users(db_session, auth_adapter)
    token = _token(auth_client, STUDENT_EMAIL, STUDENT_PASSWORD)

    response = auth_client.get(
        "/api/printers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_create_printer_as_admin(
    auth_client: TestClient, db_session: Session, auth_adapter: FakeAuthAdapter,
) -> None:
    _seed_users(db_session, auth_adapter)
    token = _token(auth_client, ADMIN_EMAIL, ADMIN_PASSWORD)

    response = auth_client.post(
        "/api/printers",
        json={"model": "Prusa CORE One", "bed_size": "250x210", "location": "Lab A"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["model"] == "Prusa CORE One"
    assert data["status"] == "idle"
    assert data["bed_size"] == "250x210"
    assert data["location"] == "Lab A"
    assert "id" in data


def test_create_printer_as_student_forbidden(
    auth_client: TestClient, db_session: Session, auth_adapter: FakeAuthAdapter,
) -> None:
    _seed_users(db_session, auth_adapter)
    token = _token(auth_client, STUDENT_EMAIL, STUDENT_PASSWORD)

    response = auth_client.post(
        "/api/printers",
        json={"model": "Prusa XL", "bed_size": "360x360", "location": "Lab B"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"


def test_get_printer_by_id(
    auth_client: TestClient, db_session: Session, auth_adapter: FakeAuthAdapter,
) -> None:
    _seed_users(db_session, auth_adapter)
    admin_token = _token(auth_client, ADMIN_EMAIL, ADMIN_PASSWORD)
    student_token = _token(auth_client, STUDENT_EMAIL, STUDENT_PASSWORD)

    # Admin creates a printer.
    create_resp = auth_client.post(
        "/api/printers",
        json={"model": "Prusa CORE One", "bed_size": "250x210", "location": "Lab A"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    printer_id = create_resp.json()["id"]

    # Student can view it.
    response = auth_client.get(
        f"/api/printers/{printer_id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    assert response.json()["model"] == "Prusa CORE One"


def test_get_printer_not_found(
    auth_client: TestClient, db_session: Session, auth_adapter: FakeAuthAdapter,
) -> None:
    _seed_users(db_session, auth_adapter)
    token = _token(auth_client, STUDENT_EMAIL, STUDENT_PASSWORD)

    response = auth_client.get(
        f"/api/printers/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "NOT_FOUND"


def test_update_printer_status(
    auth_client: TestClient, db_session: Session, auth_adapter: FakeAuthAdapter,
) -> None:
    _seed_users(db_session, auth_adapter)
    token = _token(auth_client, ADMIN_EMAIL, ADMIN_PASSWORD)

    create_resp = auth_client.post(
        "/api/printers",
        json={"model": "Prusa XL", "bed_size": "360x360", "location": "Lab B"},
        headers={"Authorization": f"Bearer {token}"},
    )
    printer_id = create_resp.json()["id"]

    response = auth_client.patch(
        f"/api/printers/{printer_id}",
        json={"status": "maintenance"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "maintenance"


def test_update_printer_as_student_forbidden(
    auth_client: TestClient, db_session: Session, auth_adapter: FakeAuthAdapter,
) -> None:
    _seed_users(db_session, auth_adapter)
    admin_token = _token(auth_client, ADMIN_EMAIL, ADMIN_PASSWORD)
    student_token = _token(auth_client, STUDENT_EMAIL, STUDENT_PASSWORD)

    create_resp = auth_client.post(
        "/api/printers",
        json={"model": "Prusa XL", "bed_size": "360x360", "location": "Lab B"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    printer_id = create_resp.json()["id"]

    response = auth_client.patch(
        f"/api/printers/{printer_id}",
        json={"status": "offline"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 403


def test_create_printer_with_material(
    auth_client: TestClient, db_session: Session, auth_adapter: FakeAuthAdapter,
) -> None:
    _seed_users(db_session, auth_adapter)
    token = _token(auth_client, ADMIN_EMAIL, ADMIN_PASSWORD)
    material = _create_material(db_session)

    response = auth_client.post(
        "/api/printers",
        json={
            "model": "Prusa CORE One",
            "bed_size": "250x210",
            "location": "Lab A",
            "current_material_id": str(material.id),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["current_material"]["name"] == "PLA Black"
    assert data["current_material"]["type"] == "PLA"


def test_update_printer_material(
    auth_client: TestClient, db_session: Session, auth_adapter: FakeAuthAdapter,
) -> None:
    _seed_users(db_session, auth_adapter)
    token = _token(auth_client, ADMIN_EMAIL, ADMIN_PASSWORD)

    # Create printer without material.
    create_resp = auth_client.post(
        "/api/printers",
        json={"model": "Prusa XL", "bed_size": "360x360", "location": "Lab B"},
        headers={"Authorization": f"Bearer {token}"},
    )
    printer_id = create_resp.json()["id"]
    assert create_resp.json()["current_material"] is None

    # Add material.
    material = _create_material(db_session)
    response = auth_client.patch(
        f"/api/printers/{printer_id}",
        json={"current_material_id": str(material.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["current_material"]["name"] == "PLA Black"
