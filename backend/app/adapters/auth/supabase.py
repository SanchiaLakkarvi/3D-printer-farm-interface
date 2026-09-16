"""Supabase Auth adapter (GoTrue HTTP). Used in real environments only."""

from __future__ import annotations

from typing import Mapping
from uuid import UUID

import httpx

from app.adapters.auth.port import AuthSession
from app.core.exceptions import BadRequestError, ConflictError, UnauthorizedError

# Sign-up waits on Supabase sending the confirmation email; that can exceed 10s.
_DEFAULT_TIMEOUT = httpx.Timeout(15.0, connect=10.0)
_SIGNUP_TIMEOUT = httpx.Timeout(45.0, connect=10.0)


class SupabaseAuthAdapter:
    """Talks to Supabase Auth public signup / token endpoints via httpx."""

    def __init__(
        self,
        *,
        base_url: str,
        service_role_key: str,
        anon_key: str,
        timeout_seconds: float | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._service_role_key = service_role_key
        self._anon_key = anon_key
        if timeout_seconds is None:
            self._timeout: httpx.Timeout = _DEFAULT_TIMEOUT
            self._signup_timeout: httpx.Timeout = _SIGNUP_TIMEOUT
        else:
            # Tests / callers that pass a single float keep the old behaviour.
            self._timeout = httpx.Timeout(timeout_seconds)
            self._signup_timeout = httpx.Timeout(timeout_seconds)

    def register(
        self,
        *,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        department: str,
        email_redirect_to: str | None = None,
    ) -> UUID:
        """Public Sign-up (anon key). Does not auto-confirm; Supabase emails the user."""
        payload: dict[str, object] = {
            "email": email,
            "password": password,
            "data": {
                "first_name": first_name,
                "last_name": last_name,
                "department": department,
            },
        }
        if email_redirect_to:
            # After confirm, land on the UI Sign-in screen (must be an allowed Redirect URL).
            payload["email_redirect_to"] = email_redirect_to
        try:
            response = httpx.post(
                f"{self._base_url}/auth/v1/signup",
                headers={
                    "apikey": self._anon_key,
                    "Authorization": f"Bearer {self._anon_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self._signup_timeout,
            )
        except httpx.TimeoutException as exc:
            raise BadRequestError(
                "AUTH_PROVIDER_TIMEOUT",
                "Sign-up timed out while contacting the authentication provider. "
                "If a confirmation email arrived, confirm it and sign in; "
                "otherwise wait a moment and try again.",
            ) from exc
        except httpx.RequestError as exc:
            raise BadRequestError(
                "AUTH_PROVIDER_ERROR",
                "Unable to reach the authentication provider. Please try again.",
            ) from exc
        if response.status_code in {400, 422} and "already" in response.text.lower():
            raise ConflictError("An account with this email already exists")
        # Supabase free-tier email sending is tightly rate-limited; surface that clearly.
        if response.status_code == 429 or "rate_limit" in response.text.lower():
            raise BadRequestError(
                "AUTH_EMAIL_RATE_LIMIT",
                "Too many confirmation emails were sent recently. "
                "Wait about an hour, then try Sign-up again "
                "(or sign in if you already confirmed).",
            )
        if response.status_code >= 400:
            raise BadRequestError(
                "AUTH_PROVIDER_ERROR",
                "Unable to register with the authentication provider",
            )
        body = response.json()
        user = body.get("user") or body
        user_id = user.get("id") if isinstance(user, dict) else None
        if not user_id:
            raise BadRequestError(
                "AUTH_PROVIDER_ERROR",
                "Authentication provider returned an unexpected response",
            )
        return UUID(str(user_id))

    def sign_in(self, *, email: str, password: str) -> AuthSession:
        try:
            response = httpx.post(
                f"{self._base_url}/auth/v1/token?grant_type=password",
                headers={
                    "apikey": self._anon_key,
                    "Authorization": f"Bearer {self._anon_key}",
                    "Content-Type": "application/json",
                },
                json={"email": email, "password": password},
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            raise BadRequestError(
                "AUTH_PROVIDER_TIMEOUT",
                "Sign-in timed out. Please try again.",
            ) from exc
        except httpx.RequestError as exc:
            raise BadRequestError(
                "AUTH_PROVIDER_ERROR",
                "Unable to reach the authentication provider. Please try again.",
            ) from exc
        if response.status_code in {400, 401}:
            raise UnauthorizedError("Invalid email or password")
        if response.status_code >= 400:
            raise BadRequestError(
                "AUTH_PROVIDER_ERROR",
                "Unable to sign in with the authentication provider",
            )
        payload = response.json()
        token = payload.get("access_token")
        user = payload.get("user") or {}
        user_id = user.get("id")
        if not token or not user_id:
            raise BadRequestError(
                "AUTH_PROVIDER_ERROR",
                "Authentication provider returned an unexpected response",
            )
        metadata = user.get("user_metadata") or {}
        if not isinstance(metadata, Mapping):
            metadata = {}
        return AuthSession(
            access_token=str(token),
            user_id=UUID(str(user_id)),
            user_metadata=dict(metadata),
        )

    def validate_token(self, token: str) -> UUID:
        try:
            response = httpx.get(
                f"{self._base_url}/auth/v1/user",
                headers={
                    "apikey": self._anon_key,
                    "Authorization": f"Bearer {token}",
                },
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            raise BadRequestError(
                "AUTH_PROVIDER_TIMEOUT",
                "Session validation timed out. Please try again.",
            ) from exc
        except httpx.RequestError as exc:
            raise BadRequestError(
                "AUTH_PROVIDER_ERROR",
                "Unable to reach the authentication provider. Please try again.",
            ) from exc
        if response.status_code in {401, 403}:
            raise UnauthorizedError("Invalid or expired token")
        if response.status_code >= 400:
            raise BadRequestError(
                "AUTH_PROVIDER_ERROR",
                "Unable to validate the session token",
            )
        user_id = response.json().get("id")
        if not user_id:
            raise UnauthorizedError("Invalid or expired token")
        return UUID(str(user_id))

    def confirm_email_token(
        self,
        *,
        token_hash: str,
        type: str = "signup",
    ) -> None:
        """Confirm via POST /verify so mail-scanner GETs cannot finish Sign-up alone."""
        confirm_type = type.strip().lower() or "signup"
        if confirm_type not in {"signup", "email"}:
            raise BadRequestError(
                "INVALID_CONFIRMATION_TYPE",
                "Unsupported email confirmation type",
            )
        try:
            response = httpx.post(
                f"{self._base_url}/auth/v1/verify",
                headers={
                    "apikey": self._anon_key,
                    "Authorization": f"Bearer {self._anon_key}",
                    "Content-Type": "application/json",
                },
                json={"type": confirm_type, "token_hash": token_hash.strip()},
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            raise BadRequestError(
                "AUTH_PROVIDER_TIMEOUT",
                "Email confirmation timed out. Please try again.",
            ) from exc
        except httpx.RequestError as exc:
            raise BadRequestError(
                "AUTH_PROVIDER_ERROR",
                "Unable to reach the authentication provider. Please try again.",
            ) from exc
        if response.status_code in {400, 401, 403, 404, 422}:
            raise UnauthorizedError("Invalid or expired confirmation link")
        if response.status_code >= 400:
            raise BadRequestError(
                "AUTH_PROVIDER_ERROR",
                "Unable to confirm the email address",
            )

    def delete_user(self, user_id: UUID) -> None:
        try:
            httpx.delete(
                f"{self._base_url}/auth/v1/admin/users/{user_id}",
                headers=self._admin_headers(),
                timeout=self._timeout,
            )
        except httpx.RequestError:
            # Best-effort cleanup; callers already treat this as non-critical.
            return

    def _admin_headers(self) -> dict[str, str]:
        return {
            "apikey": self._service_role_key,
            "Authorization": f"Bearer {self._service_role_key}",
            "Content-Type": "application/json",
        }
