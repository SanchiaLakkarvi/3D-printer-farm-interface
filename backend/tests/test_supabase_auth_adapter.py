"""Unit tests for Supabase Auth adapter error mapping (no real network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from app.adapters.auth.supabase import SupabaseAuthAdapter
from app.core.exceptions import BadRequestError, ConflictError


def _adapter() -> SupabaseAuthAdapter:
    return SupabaseAuthAdapter(
        base_url="https://example.supabase.co",
        service_role_key="service",
        anon_key="anon",
        timeout_seconds=1.0,
    )


def test_register_maps_timeout_to_bad_request() -> None:
    with patch(
        "app.adapters.auth.supabase.httpx.post",
        side_effect=httpx.ReadTimeout("timed out"),
    ):
        with pytest.raises(BadRequestError) as exc_info:
            _adapter().register(
                email="22701234@student.uwa.edu.au",
                password="secure-password-1",
                first_name="Ada",
                last_name="Lovelace",
                department="engineering",
            )
    assert exc_info.value.detail["code"] == "AUTH_PROVIDER_TIMEOUT"


def test_register_maps_duplicate_to_conflict() -> None:
    response = MagicMock()
    response.status_code = 400
    response.text = "User already registered"
    with patch("app.adapters.auth.supabase.httpx.post", return_value=response):
        with pytest.raises(ConflictError):
            _adapter().register(
                email="22701234@student.uwa.edu.au",
                password="secure-password-1",
                first_name="Ada",
                last_name="Lovelace",
                department="engineering",
            )


def test_register_maps_email_rate_limit_to_bad_request() -> None:
    response = MagicMock()
    response.status_code = 429
    response.text = '{"error_code":"over_email_send_rate_limit"}'
    with patch("app.adapters.auth.supabase.httpx.post", return_value=response):
        with pytest.raises(BadRequestError) as exc_info:
            _adapter().register(
                email="22701234@student.uwa.edu.au",
                password="secure-password-1",
                first_name="Ada",
                last_name="Lovelace",
                department="engineering",
            )
    assert exc_info.value.detail["code"] == "AUTH_EMAIL_RATE_LIMIT"


def test_register_returns_user_id_on_success() -> None:
    user_id = uuid4()
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"user": {"id": str(user_id)}}
    with patch("app.adapters.auth.supabase.httpx.post", return_value=response):
        result = _adapter().register(
            email="22701234@student.uwa.edu.au",
            password="secure-password-1",
            first_name="Ada",
            last_name="Lovelace",
            department="engineering",
            email_redirect_to="http://localhost:5173/?email_confirmed=1",
        )
    assert result == user_id


def test_confirm_email_token_posts_verify() -> None:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"access_token": "tok", "user": {"id": str(uuid4())}}
    with patch("app.adapters.auth.supabase.httpx.post", return_value=response) as post:
        _adapter().confirm_email_token(token_hash="abc123hash", type="signup")
    post.assert_called_once()
    assert post.call_args.args[0].endswith("/auth/v1/verify")
    assert post.call_args.kwargs["json"] == {
        "type": "signup",
        "token_hash": "abc123hash",
    }


def test_confirm_email_token_maps_invalid_to_unauthorized() -> None:
    response = MagicMock()
    response.status_code = 403
    response.text = "forbidden"
    with patch("app.adapters.auth.supabase.httpx.post", return_value=response):
        with pytest.raises(Exception) as exc_info:
            _adapter().confirm_email_token(token_hash="bad-token-hash", type="signup")
    from app.core.exceptions import UnauthorizedError

    assert isinstance(exc_info.value, UnauthorizedError)


def test_confirm_signup_otp_posts_verify_with_email_token() -> None:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"access_token": "tok", "user": {"id": str(uuid4())}}
    with patch("app.adapters.auth.supabase.httpx.post", return_value=response) as post:
        _adapter().confirm_signup_otp(
            email="22701234@student.uwa.edu.au",
            token="123456",
        )
    post.assert_called_once()
    assert post.call_args.args[0].endswith("/auth/v1/verify")
    assert post.call_args.kwargs["json"] == {
        "type": "signup",
        "email": "22701234@student.uwa.edu.au",
        "token": "123456",
    }


def test_confirm_signup_otp_maps_invalid_to_unauthorized() -> None:
    from app.core.exceptions import UnauthorizedError

    response = MagicMock()
    response.status_code = 401
    response.text = "invalid"
    with patch("app.adapters.auth.supabase.httpx.post", return_value=response):
        with pytest.raises(UnauthorizedError) as exc_info:
            _adapter().confirm_signup_otp(
                email="22701234@student.uwa.edu.au",
                token="000000",
            )
    assert "verification code" in str(exc_info.value.detail["message"]).lower()


def test_resend_signup_posts_resend_body() -> None:
    response = MagicMock()
    response.status_code = 200
    response.text = "{}"
    with patch("app.adapters.auth.supabase.httpx.post", return_value=response) as post:
        _adapter().resend_signup(
            email="22701234@student.uwa.edu.au",
            email_redirect_to="http://localhost:5173",
        )
    post.assert_called_once()
    assert post.call_args.args[0].endswith("/auth/v1/resend")
    assert post.call_args.kwargs["json"] == {
        "type": "signup",
        "email": "22701234@student.uwa.edu.au",
        "email_redirect_to": "http://localhost:5173",
    }


def test_resend_signup_maps_rate_limit() -> None:
    response = MagicMock()
    response.status_code = 429
    response.text = '{"error_code":"over_email_send_rate_limit"}'
    with patch("app.adapters.auth.supabase.httpx.post", return_value=response):
        with pytest.raises(BadRequestError) as exc_info:
            _adapter().resend_signup(email="22701234@student.uwa.edu.au")
    assert exc_info.value.detail["code"] == "AUTH_EMAIL_RATE_LIMIT"
