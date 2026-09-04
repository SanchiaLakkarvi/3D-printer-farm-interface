"""In-memory Auth adapter for tests — no real Supabase Auth calls."""

from __future__ import annotations

from uuid import UUID, uuid4

from app.adapters.auth.port import AuthSession
from app.core.exceptions import ConflictError, UnauthorizedError


class FakeAuthAdapter:
    """Deterministic AuthPort for HTTP tests and local demos without Supabase."""

    def __init__(self) -> None:
        self._by_email: dict[str, tuple[UUID, str]] = {}
        self._tokens: dict[str, UUID] = {}

    def register(self, *, email: str, password: str) -> UUID:
        normalized = email.strip().lower()
        if normalized in self._by_email:
            raise ConflictError("An account with this email already exists")
        user_id = uuid4()
        self._by_email[normalized] = (user_id, password)
        return user_id

    def sign_in(self, *, email: str, password: str) -> AuthSession:
        normalized = email.strip().lower()
        record = self._by_email.get(normalized)
        if record is None or record[1] != password:
            raise UnauthorizedError("Invalid email or password")
        user_id = record[0]
        token = f"fake-token-{user_id}"
        self._tokens[token] = user_id
        return AuthSession(access_token=token, user_id=user_id)

    def validate_token(self, token: str) -> UUID:
        user_id = self._tokens.get(token)
        if user_id is None:
            raise UnauthorizedError("Invalid or expired token")
        return user_id

    def expire_token(self, token: str) -> None:
        """Drop a session token so validate_token rejects it as expired."""
        self._tokens.pop(token, None)

    def delete_user(self, user_id: UUID) -> None:
        email_to_drop = next(
            (email for email, (uid, _) in self._by_email.items() if uid == user_id),
            None,
        )
        if email_to_drop is not None:
            del self._by_email[email_to_drop]
        expired = [token for token, uid in self._tokens.items() if uid == user_id]
        for token in expired:
            del self._tokens[token]

    def seed_user(self, *, email: str, password: str, user_id: UUID | None = None) -> UUID:
        """Register a known Auth user for Seed User / fixture setup."""
        normalized = email.strip().lower()
        if normalized in self._by_email:
            raise ConflictError("An account with this email already exists")
        resolved_id = user_id or uuid4()
        self._by_email[normalized] = (resolved_id, password)
        return resolved_id
