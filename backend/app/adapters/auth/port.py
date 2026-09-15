"""Auth provider port — credentials/sessions live outside the users table."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AuthSession:
    """Session issued by the Auth provider after successful Sign-in."""

    access_token: str
    user_id: UUID


class AuthPort(Protocol):
    """Narrow Supabase Auth boundary used by application services."""

    def register(self, *, email: str, password: str) -> UUID:
        """Create an Auth user; return its id (shared with the app profile)."""

    def sign_in(self, *, email: str, password: str) -> AuthSession:
        """Verify credentials and return a session token + Auth user id."""

    def validate_token(self, token: str) -> UUID:
        """Return the Auth user id for a valid access token."""

    def delete_user(self, user_id: UUID) -> None:
        """Best-effort cleanup when profile creation fails after register."""
