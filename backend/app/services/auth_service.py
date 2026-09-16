"""Authentication and profile application services."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.auth.port import AuthPort, AuthSession
from app.core.exceptions import BadRequestError, ConflictError, UnauthorizedError
from app.models.enums import UserRole
from app.models.user import User

STUDENT_EMAIL_RE = re.compile(
    r"^(?P<student_number>[A-Za-z0-9._%+-]+)@student\.uwa\.edu\.au$",
    re.IGNORECASE,
)

SIGNUP_PENDING_MESSAGE = (
    "Check your email to confirm your account, then sign in."
)

EMAIL_CONFIRM_OK_MESSAGE = "Your email is verified. Sign in with your password."


@dataclass(frozen=True, slots=True)
class SignupPendingResult:
    """Student Sign-up accepted; profile is created on first confirmed Sign-in."""

    email: str
    message: str = SIGNUP_PENDING_MESSAGE


@dataclass(frozen=True, slots=True)
class EmailConfirmResult:
    """Email confirmation completed via explicit token_hash exchange."""

    message: str = EMAIL_CONFIRM_OK_MESSAGE


def parse_student_email(email: str) -> str:
    """Validate Student Email and return the derived Student Number."""
    match = STUDENT_EMAIL_RE.fullmatch(email.strip())
    if match is None:
        raise BadRequestError(
            "INVALID_STUDENT_EMAIL",
            "Email must be of the form {student_id}@student.uwa.edu.au",
        )
    student_number = match.group("student_number")
    if not student_number:
        raise BadRequestError(
            "INVALID_STUDENT_EMAIL",
            "Email must be of the form {student_id}@student.uwa.edu.au",
        )
    return student_number


def signup_student(
    *,
    db: Session,
    auth: AuthPort,
    first_name: str,
    last_name: str,
    email: str,
    password: str,
    department: str,
    email_redirect_to: str | None = None,
) -> SignupPendingResult:
    """Register via Auth (email confirmation pending). Does not insert `users`."""
    parse_student_email(email)
    normalized_email = email.strip().lower()

    existing = db.scalar(select(User).where(User.email == normalized_email))
    if existing is not None:
        raise ConflictError("An account with this email already exists")

    auth.register(
        email=normalized_email,
        password=password,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        department=department.strip(),
        email_redirect_to=email_redirect_to,
    )
    return SignupPendingResult(email=normalized_email)


def confirm_student_email(
    *,
    auth: AuthPort,
    token_hash: str,
    type: str = "signup",
) -> EmailConfirmResult:
    """Exchange confirmation token_hash. Does not create a session or profile."""
    auth.confirm_email_token(token_hash=token_hash, type=type)
    return EmailConfirmResult()


def _metadata_str(metadata: object, key: str) -> str | None:
    if not isinstance(metadata, dict):
        return None
    value = metadata.get(key)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _create_student_profile_from_session(
    *,
    db: Session,
    session: AuthSession,
    email: str,
) -> User:
    """Create Role=student from Auth id + email + signup metadata."""
    try:
        student_number = parse_student_email(email)
    except BadRequestError:
        # Staff Auth users without a profile are not auto-provisioned as students.
        raise UnauthorizedError("Invalid email or password") from None

    first_name = _metadata_str(session.user_metadata, "first_name")
    last_name = _metadata_str(session.user_metadata, "last_name")
    department = _metadata_str(session.user_metadata, "department")
    if first_name is None or last_name is None or department is None:
        raise BadRequestError(
            "PROFILE_METADATA_MISSING",
            "Account profile metadata is incomplete; complete Sign-up again or contact support",
        )

    user = User(
        id=session.user_id,
        email=email.strip().lower(),
        first_name=first_name,
        last_name=last_name,
        student_number=student_number,
        role=UserRole.STUDENT,
        department=department,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.get(User, session.user_id)
        if existing is not None:
            return existing
        raise ConflictError("An account with this email already exists") from None
    db.refresh(user)
    return user


def sign_in(
    *,
    db: Session,
    auth: AuthPort,
    email: str,
    password: str,
) -> tuple[AuthSession, User]:
    """Authenticate; load profile or create student profile on first confirmed Sign-in."""
    normalized_email = email.strip().lower()
    session = auth.sign_in(email=normalized_email, password=password)
    user = db.get(User, session.user_id)
    if user is None:
        user = _create_student_profile_from_session(
            db=db,
            session=session,
            email=normalized_email,
        )
    return session, user


def get_profile_for_token(*, db: Session, auth: AuthPort, token: str) -> User:
    user_id = auth.validate_token(token)
    user = db.get(User, user_id)
    if user is None:
        raise UnauthorizedError("Invalid or expired token")
    return user
