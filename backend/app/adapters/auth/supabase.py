"""Supabase Auth adapter (GoTrue HTTP). Used in real environments only."""

from __future__ import annotations

from uuid import UUID

import httpx

from app.adapters.auth.port import AuthSession
from app.core.exceptions import BadRequestError, ConflictError, UnauthorizedError


class SupabaseAuthAdapter:
    """Talks to Supabase Auth Admin / token endpoints via httpx."""

    def __init__(
        self,
        *,
        base_url: str,
        service_role_key: str,
        anon_key: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._service_role_key = service_role_key
        self._anon_key = anon_key
        self._timeout = timeout_seconds

    def register(self, *, email: str, password: str) -> UUID:
        response = httpx.post(
            f"{self._base_url}/auth/v1/admin/users",
            headers=self._admin_headers(),
            json={
                "email": email,
                "password": password,
                "email_confirm": True,
            },
            timeout=self._timeout,
        )
        if response.status_code in {400, 422} and "already" in response.text.lower():
            raise ConflictError("An account with this email already exists")
        if response.status_code >= 400:
            raise BadRequestError(
                "AUTH_PROVIDER_ERROR",
                "Unable to register with the authentication provider",
            )
        user_id = response.json().get("id")
        if not user_id:
            raise BadRequestError(
                "AUTH_PROVIDER_ERROR",
                "Authentication provider returned an unexpected response",
            )
        return UUID(str(user_id))

    def sign_in(self, *, email: str, password: str) -> AuthSession:
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
        return AuthSession(access_token=str(token), user_id=UUID(str(user_id)))

    def validate_token(self, token: str) -> UUID:
        response = httpx.get(
            f"{self._base_url}/auth/v1/user",
            headers={
                "apikey": self._anon_key,
                "Authorization": f"Bearer {token}",
            },
            timeout=self._timeout,
        )
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

    def delete_user(self, user_id: UUID) -> None:
        httpx.delete(
            f"{self._base_url}/auth/v1/admin/users/{user_id}",
            headers=self._admin_headers(),
            timeout=self._timeout,
        )

    def _admin_headers(self) -> dict[str, str]:
        return {
            "apikey": self._service_role_key,
            "Authorization": f"Bearer {self._service_role_key}",
            "Content-Type": "application/json",
        }
