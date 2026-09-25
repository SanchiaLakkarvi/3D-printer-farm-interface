"""In-memory Auth adapter for tests — no real Supabase Auth calls."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from app.adapters.auth.port import AuthSession
from app.core.exceptions import ConflictError, UnauthorizedError


# Deterministic OTP for Fake Auth tests (matches UI 6-digit entry).
FAKE_SIGNUP_OTP = "123456"


@dataclass
class _AuthRecord:
    user_id: UUID
    password: str
    confirmed: bool
    metadata: dict[str, str] = field(default_factory=dict)
    signup_otp: str = FAKE_SIGNUP_OTP


class FakeAuthAdapter:
    """Deterministic AuthPort for HTTP tests and local demos without Supabase."""

    def __init__(self) -> None:
        self._by_email: dict[str, _AuthRecord] = {}
        self._tokens: dict[str, UUID] = {}
        self._confirm_tokens: dict[str, str] = {}
        self.last_email_redirect_to: str | None = None
        self.last_confirm_token_hash: str | None = None
        self.last_resend_email: str | None = None

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
        self.last_email_redirect_to = email_redirect_to
        normalized = email.strip().lower()
        if normalized in self._by_email:
            raise ConflictError("An account with this email already exists")
        user_id = uuid4()
        self._by_email[normalized] = _AuthRecord(
            user_id=user_id,
            password=password,
            confirmed=False,
            metadata={
                "first_name": first_name,
                "last_name": last_name,
                "department": department,
            },
            signup_otp=FAKE_SIGNUP_OTP,
        )
        # Deterministic token for tests: confirm via token_hash without auto-confirm on register.
        self._confirm_tokens[f"confirm-{normalized}"] = normalized
        return user_id

    def confirm_email(self, email: str) -> None:
        """Mark a registered user as email-confirmed (test/ops helper)."""
        normalized = email.strip().lower()
        record = self._by_email.get(normalized)
        if record is None:
            raise UnauthorizedError("Invalid email or password")
        record.confirmed = True

    def confirm_email_token(
        self,
        *,
        token_hash: str,
        type: str = "signup",
    ) -> None:
        """Confirm via token_hash issued at register (simulates POST /verify)."""
        del type  # Fake ignores type; production adapter forwards it.
        self.last_confirm_token_hash = token_hash
        email = self._confirm_tokens.get(token_hash)
        if email is None:
            raise UnauthorizedError("Invalid or expired confirmation link")
        self.confirm_email(email)

    def confirm_signup_otp(self, *, email: str, token: str) -> None:
        """Confirm via emailed 6-digit OTP issued at register."""
        normalized = email.strip().lower()
        record = self._by_email.get(normalized)
        if record is None or record.signup_otp != token.strip():
            raise UnauthorizedError("Invalid or expired verification code")
        if record.confirmed:
            raise UnauthorizedError("Invalid or expired verification code")
        record.confirmed = True

    def resend_signup(
        self,
        *,
        email: str,
        email_redirect_to: str | None = None,
    ) -> None:
        """Refresh OTP for an unconfirmed registered email (test no-op refresh)."""
        self.last_email_redirect_to = email_redirect_to
        normalized = email.strip().lower()
        self.last_resend_email = normalized
        record = self._by_email.get(normalized)
        if record is None:
            raise UnauthorizedError("Invalid or expired verification code")
        if record.confirmed:
            raise UnauthorizedError("Invalid or expired verification code")
        record.signup_otp = FAKE_SIGNUP_OTP

    def sign_in(self, *, email: str, password: str) -> AuthSession:
        normalized = email.strip().lower()
        record = self._by_email.get(normalized)
        if record is None or record.password != password:
            raise UnauthorizedError("Invalid email or password")
        if not record.confirmed:
            raise UnauthorizedError("Invalid email or password")
        token = f"fake-token-{record.user_id}"
        self._tokens[token] = record.user_id
        return AuthSession(
            access_token=token,
            user_id=record.user_id,
            user_metadata=dict(record.metadata),
        )

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
            (email for email, record in self._by_email.items() if record.user_id == user_id),
            None,
        )
        if email_to_drop is not None:
            del self._by_email[email_to_drop]
        expired = [token for token, uid in self._tokens.items() if uid == user_id]
        for token in expired:
            del self._tokens[token]

    def seed_user(self, *, email: str, password: str, user_id: UUID | None = None) -> UUID:
        """Register a confirmed Auth user for Seed User / fixture setup."""
        normalized = email.strip().lower()
        if normalized in self._by_email:
            raise ConflictError("An account with this email already exists")
        resolved_id = user_id or uuid4()
        self._by_email[normalized] = _AuthRecord(
            user_id=resolved_id,
            password=password,
            confirmed=True,
            metadata={},
        )
        return resolved_id
