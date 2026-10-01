"""Auth provider port — credentials/sessions live outside the users table."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AuthSession:
    """Session issued by the Auth provider after successful Sign-in."""

    access_token: str
    user_id: UUID
    user_metadata: Mapping[str, object] = field(default_factory=dict)


class AuthPort(Protocol):
    """Narrow Supabase Auth boundary used by application services."""

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
        """Create an Auth user with profile metadata; return its id."""

    def sign_in(self, *, email: str, password: str) -> AuthSession:
        """Verify credentials and return a session token + Auth user id."""

    def validate_token(self, token: str) -> UUID:
        """Return the Auth user id for a valid access token."""

    def confirm_email_token(
        self,
        *,
        token_hash: str,
        type: str = "signup",
    ) -> None:
        """Confirm email via token_hash (POST). Do not confirm on email-link GET alone."""

    def confirm_signup_otp(self, *, email: str, token: str) -> None:
        """Confirm signup via emailed 6-digit OTP. Discard any returned session."""

    def resend_signup(
        self,
        *,
        email: str,
        email_redirect_to: str | None = None,
    ) -> None:
        """Resend the signup confirmation email / OTP for an unconfirmed Auth user."""

    def delete_user(self, user_id: UUID) -> None:
        """Best-effort cleanup when profile creation fails after register."""
