"""HTTP tests for Sign-in, /me, and token rejection (Fake Auth + in-memory DB)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.auth.fake import FakeAuthAdapter
from app.models.enums import UserRole
from app.models.user import User

STUDENT_EMAIL = "22705555@student.uwa.edu.au"
STUDENT_PASSWORD = "secure-password-1"


def _signup_student(auth_client: TestClient) -> dict:
    response = auth_client.post(
        "/api/auth/signup",
        json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": STUDENT_EMAIL,
            "password": STUDENT_PASSWORD,
            "department": "engineering",
        },
    )
    assert response.status_code == 201
    return response.json()


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


def test_signin_success_returns_token_and_safe_profile(auth_client: TestClient) -> None:
    profile = _signup_student(auth_client)

    response = auth_client.post(
        "/api/auth/signin",
        json={"email": STUDENT_EMAIL, "password": STUDENT_PASSWORD},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and body["access_token"]
    assert body["user"]["id"] == profile["id"]
    assert body["user"]["email"] == STUDENT_EMAIL
    assert body["user"]["first_name"] == "Ada"
    assert body["user"]["last_name"] == "Lovelace"
    assert body["user"]["role"] == "student"
    assert body["user"]["department"] == "engineering"
    assert body["user"]["student_number"] == "22705555"
    assert "password" not in body
    assert "password" not in body["user"]


def test_signin_succeeds_for_farmer_and_admin_roles(
    auth_client: TestClient,
    db_session: Session,
    auth_adapter: FakeAuthAdapter,
) -> None:
    _seed_profile(
        db_session=db_session,
        auth_adapter=auth_adapter,
        email="farmer1@uwa.edu.au",
        password="farmer-password-1",
        role=UserRole.FARMER,
        first_name="Fran",
        last_name="Farmer",
    )
    _seed_profile(
        db_session=db_session,
        auth_adapter=auth_adapter,
        email="christopher.lamb@uwa.edu.au",
        password="admin-password-1",
        role=UserRole.ADMIN,
        first_name="Christopher",
        last_name="Lamb",
    )

    farmer = auth_client.post(
        "/api/auth/signin",
        json={"email": "farmer1@uwa.edu.au", "password": "farmer-password-1"},
    )
    assert farmer.status_code == 200
    assert farmer.json()["user"]["role"] == "farmer"
    assert farmer.json()["user"]["student_number"] is None

    admin = auth_client.post(
        "/api/auth/signin",
        json={
            "email": "christopher.lamb@uwa.edu.au",
            "password": "admin-password-1",
        },
    )
    assert admin.status_code == 200
    assert admin.json()["user"]["role"] == "admin"


def test_signin_rejects_bad_password(auth_client: TestClient) -> None:
    _signup_student(auth_client)

    response = auth_client.post(
        "/api/auth/signin",
        json={"email": STUDENT_EMAIL, "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "UNAUTHORIZED"
    # Same message as unknown email — do not leak whether the account exists.
    assert response.json()["detail"]["message"] == "Invalid email or password"


def test_signin_rejects_unknown_email(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/auth/signin",
        json={"email": "nobody@student.uwa.edu.au", "password": "anything-here"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["message"] == "Invalid email or password"


def test_signin_loads_role_from_profile_ignores_client_role(
    auth_client: TestClient,
) -> None:
    _signup_student(auth_client)

    response = auth_client.post(
        "/api/auth/signin",
        json={
            "email": STUDENT_EMAIL,
            "password": STUDENT_PASSWORD,
            "role": "admin",
        },
    )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "student"


def test_me_returns_profile_for_token_subject(auth_client: TestClient) -> None:
    profile = _signup_student(auth_client)
    signin = auth_client.post(
        "/api/auth/signin",
        json={"email": STUDENT_EMAIL, "password": STUDENT_PASSWORD},
    )
    token = signin.json()["access_token"]

    response = auth_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == profile["id"]
    assert body["email"] == STUDENT_EMAIL
    assert body["role"] == "student"
    assert "password" not in body


def test_me_rejects_missing_token(auth_client: TestClient) -> None:
    response = auth_client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "UNAUTHORIZED"


def test_me_rejects_invalid_token(auth_client: TestClient) -> None:
    response = auth_client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "UNAUTHORIZED"


def test_me_rejects_expired_token(
    auth_client: TestClient,
    auth_adapter: FakeAuthAdapter,
) -> None:
    _signup_student(auth_client)
    signin = auth_client.post(
        "/api/auth/signin",
        json={"email": STUDENT_EMAIL, "password": STUDENT_PASSWORD},
    )
    token = signin.json()["access_token"]
    auth_adapter.expire_token(token)

    response = auth_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "UNAUTHORIZED"


def test_signout_returns_204_without_server_session(auth_client: TestClient) -> None:
    response = auth_client.post("/api/auth/signout")
    assert response.status_code == 204


def test_signout_does_not_revoke_existing_bearer_token(auth_client: TestClient) -> None:
    """Server Sign-out is a no-op; clients must discard the token locally."""
    _signup_student(auth_client)
    token = auth_client.post(
        "/api/auth/signin",
        json={"email": STUDENT_EMAIL, "password": STUDENT_PASSWORD},
    ).json()["access_token"]

    assert auth_client.post("/api/auth/signout").status_code == 204
    still_valid = auth_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert still_valid.status_code == 200
