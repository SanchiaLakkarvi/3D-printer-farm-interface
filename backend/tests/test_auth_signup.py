"""HTTP tests for Student Sign-up (Fake Auth + in-memory DB)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.auth.fake import FakeAuthAdapter
from app.models.user import User


def test_student_signup_pending_does_not_create_users_row(
    auth_client: TestClient,
    db_session: Session,
    auth_adapter: FakeAuthAdapter,
) -> None:
    response = auth_client.post(
        "/api/auth/signup",
        json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "22701234@student.uwa.edu.au",
            "password": "secure-password-1",
            "department": "engineering",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "22701234@student.uwa.edu.au"
    assert "check your email" in body["message"].lower()
    assert "id" not in body
    assert "role" not in body
    assert "password" not in body
    assert db_session.scalar(select(User).where(User.email == body["email"])) is None
    assert auth_adapter.last_email_redirect_to == (
        "http://localhost:5173"
    )


def test_student_signup_rejects_wrong_email_domain(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/auth/signup",
        json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@uwa.edu.au",
            "password": "secure-password-1",
            "department": "engineering",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_STUDENT_EMAIL"


def test_student_signup_rejects_empty_local_part(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/auth/signup",
        json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "@student.uwa.edu.au",
            "password": "secure-password-1",
            "department": "engineering",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_STUDENT_EMAIL"


def test_student_signup_rejects_duplicate_email(auth_client: TestClient) -> None:
    payload = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "22709999@student.uwa.edu.au",
        "password": "secure-password-1",
        "department": "IT",
    }
    assert auth_client.post("/api/auth/signup", json=payload).status_code == 201
    response = auth_client.post("/api/auth/signup", json=payload)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "CONFLICT"


def test_student_signup_ignores_client_supplied_role(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/auth/signup",
        json={
            "first_name": "Eve",
            "last_name": "Admin",
            "email": "22708888@student.uwa.edu.au",
            "password": "secure-password-1",
            "department": "mechanical",
            "role": "admin",
        },
    )
    assert response.status_code == 201
    assert "role" not in response.json()
    assert response.json()["email"] == "22708888@student.uwa.edu.au"


def test_signin_before_confirm_is_rejected(
    auth_client: TestClient,
    db_session: Session,
) -> None:
    assert (
        auth_client.post(
            "/api/auth/signup",
            json={
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": "22706666@student.uwa.edu.au",
                "password": "secure-password-1",
                "department": "engineering",
            },
        ).status_code
        == 201
    )
    response = auth_client.post(
        "/api/auth/signin",
        json={
            "email": "22706666@student.uwa.edu.au",
            "password": "secure-password-1",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "UNAUTHORIZED"
    assert (
        db_session.scalar(
            select(User).where(User.email == "22706666@student.uwa.edu.au")
        )
        is None
    )


def test_signin_after_confirm_creates_student_profile(
    auth_client: TestClient,
    auth_adapter: FakeAuthAdapter,
    db_session: Session,
) -> None:
    email = "22707777@student.uwa.edu.au"
    assert (
        auth_client.post(
            "/api/auth/signup",
            json={
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": email,
                "password": "secure-password-1",
                "department": "engineering",
            },
        ).status_code
        == 201
    )
    auth_adapter.confirm_email(email)

    response = auth_client.post(
        "/api/auth/signin",
        json={"email": email, "password": "secure-password-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == email
    assert body["user"]["role"] == "student"
    assert body["user"]["first_name"] == "Ada"
    assert body["user"]["last_name"] == "Lovelace"
    assert body["user"]["department"] == "engineering"
    assert body["user"]["student_number"] == "22707777"

    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    assert user.role.value == "student"
    assert str(user.id) == body["user"]["id"]


def test_confirm_email_via_token_hash_then_signin(
    auth_client: TestClient,
    db_session: Session,
) -> None:
    email = "22708888@student.uwa.edu.au"
    assert (
        auth_client.post(
            "/api/auth/signup",
            json={
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": email,
                "password": "secure-password-1",
                "department": "engineering",
            },
        ).status_code
        == 201
    )

    confirm = auth_client.post(
        "/api/auth/confirm-email",
        json={"token_hash": f"confirm-{email}", "type": "signup"},
    )
    assert confirm.status_code == 200
    assert "verified" in confirm.json()["message"].lower()

    response = auth_client.post(
        "/api/auth/signin",
        json={"email": email, "password": "secure-password-1"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == email
    assert (
        db_session.scalar(select(User).where(User.email == email)) is not None
    )


def test_confirm_email_rejects_unknown_token(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/auth/confirm-email",
        json={"token_hash": "missing-token-hash-xx", "type": "signup"},
    )
    assert response.status_code == 401
