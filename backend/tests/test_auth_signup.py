"""HTTP tests for Student Sign-up (Fake Auth + in-memory DB)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_student_signup_success_creates_student_profile(auth_client: TestClient) -> None:
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
    assert body["first_name"] == "Ada"
    assert body["last_name"] == "Lovelace"
    assert body["role"] == "student"
    assert body["student_number"] == "22701234"
    assert body["department"] == "engineering"
    assert "id" in body
    assert "password" not in body
    assert "auth_hash" not in body


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
    assert response.json()["role"] == "student"
