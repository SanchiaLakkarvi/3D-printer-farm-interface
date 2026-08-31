"""Authentication and profile application services."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

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


class SeedSettings(Protocol):
    """Env/config surface for Seed User emails and distinct passwords."""

    seed_admin_email: str
    seed_admin_password: str
    seed_farmer1_email: str
    seed_farmer1_password: str
    seed_farmer2_email: str
    seed_farmer2_password: str
    seed_farmer3_email: str
    seed_farmer3_password: str


@dataclass(frozen=True, slots=True)
class SeedUserSpec:
    email: str
    password: str
    role: UserRole
    first_name: str
    last_name: str


def _seed_specs(settings: SeedSettings) -> list[SeedUserSpec]:
    return [
        SeedUserSpec(
            email=settings.seed_admin_email,
            password=settings.seed_admin_password,
            role=UserRole.ADMIN,
            first_name="Christopher",
            last_name="Lamb",
        ),
        SeedUserSpec(
            email=settings.seed_farmer1_email,
            password=settings.seed_farmer1_password,
            role=UserRole.FARMER,
            first_name="Farmer",
            last_name="One",
        ),
        SeedUserSpec(
            email=settings.seed_farmer2_email,
            password=settings.seed_farmer2_password,
            role=UserRole.FARMER,
            first_name="Farmer",
            last_name="Two",
        ),
        SeedUserSpec(
            email=settings.seed_farmer3_email,
            password=settings.seed_farmer3_password,
            role=UserRole.FARMER,
            first_name="Farmer",
            last_name="Three",
        ),
    ]


def seed_demo_users(
    *,
    db: Session,
    auth: AuthPort,
    settings: SeedSettings,
) -> list[User]:
    """Create Seed Users in Auth + application profiles (demo/ops tooling).

    Distinct passwords must come from env/seed config. Profiles use null
    student_number and share the Auth UUID. Not Student Sign-up.
    """
    specs = _seed_specs(settings)
    passwords = [spec.password.strip() for spec in specs]
    if any(not password for password in passwords):
        raise BadRequestError(
            "SEED_PASSWORD_REQUIRED",
            "Each Seed User needs a non-empty password in env/seed config",
        )
    if len(set(passwords)) != len(passwords):
        raise BadRequestError(
            "SEED_PASSWORD_REQUIRED",
            "Each Seed User must have a distinct password in env/seed config",
        )

    created: list[User] = []
    for spec in specs:
        user = _create_seed_user(db=db, auth=auth, spec=spec)
        created.append(user)
    return created


def _create_seed_user(*, db: Session, auth: AuthPort, spec: SeedUserSpec) -> User:
    normalized_email = spec.email.strip().lower()
    existing = db.scalar(select(User).where(User.email == normalized_email))
    if existing is not None:
        raise ConflictError(f"Seed User already exists: {normalized_email}")

    auth_user_id = auth.register(email=normalized_email, password=spec.password)
    user = User(
        id=auth_user_id,
        email=normalized_email,
        first_name=spec.first_name,
        last_name=spec.last_name,
        student_number=None,
        role=spec.role,
        department=None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        auth.delete_user(auth_user_id)
        raise ConflictError(f"Seed User already exists: {normalized_email}") from None
    db.refresh(user)
    return user


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
) -> User:
    """Register via Auth, then create a Role=student profile with the same UUID."""
    student_number = parse_student_email(email)
    normalized_email = email.strip().lower()

    existing = db.scalar(select(User).where(User.email == normalized_email))
    if existing is not None:
        raise ConflictError("An account with this email already exists")

    auth_user_id = auth.register(email=normalized_email, password=password)
    user = User(
        id=auth_user_id,
        email=normalized_email,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        student_number=student_number,
        role=UserRole.STUDENT,
        department=department.strip(),
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        auth.delete_user(auth_user_id)
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
    """Authenticate with Auth provider and load the application profile Role."""
    session = auth.sign_in(email=email.strip().lower(), password=password)
    user = db.get(User, session.user_id)
    if user is None:
        raise UnauthorizedError("Invalid email or password")
    return session, user


def get_profile_for_token(*, db: Session, auth: AuthPort, token: str) -> User:
    user_id = auth.validate_token(token)
    user = db.get(User, user_id)
    if user is None:
        raise UnauthorizedError("Invalid or expired token")
    return user
