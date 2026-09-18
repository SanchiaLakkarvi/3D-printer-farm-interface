"""Demo accounts for the fake auth adapter.

The fake adapter keeps logins in memory but profiles live in Postgres, so after a
backend restart an account exists in the database yet cannot sign in, and signing
up again fails with 409. Seeding the accounts on every start avoids that: each
one is registered again, reusing the id of any profile already saved, so its role
and job history are kept.

Format (env ``DEMO_ACCOUNTS``): ``email:password:role`` entries separated by
commas; role is ``student`` (default), ``farmer`` or ``admin``. Passwords must not
contain ``:`` or ``,``. Only used with AUTH_ADAPTER=fake.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.auth.fake import FakeAuthAdapter
from app.core.exceptions import BadRequestError, ConflictError
from app.models.enums import UserRole
from app.models.user import User
from app.services.auth_service import parse_student_email


@dataclass(frozen=True)
class DemoAccount:
    email: str
    password: str
    role: UserRole


def parse_demo_accounts(raw: str) -> list[DemoAccount]:
    accounts: list[DemoAccount] = []
    for entry in (part.strip() for part in raw.split(",")):
        if not entry:
            continue
        fields = entry.split(":")
        if len(fields) not in (2, 3) or not fields[0].strip() or not fields[1]:
            raise ValueError(
                f"Bad DEMO_ACCOUNTS entry {entry!r}: expected email:password[:role]"
            )
        role_text = fields[2].strip().lower() if len(fields) == 3 else "student"
        try:
            role = UserRole(role_text)
        except ValueError:
            allowed = ", ".join(r.value for r in UserRole)
            raise ValueError(
                f"Bad role {role_text!r} in DEMO_ACCOUNTS; use one of: {allowed}"
            ) from None
        accounts.append(DemoAccount(fields[0].strip().lower(), fields[1], role))
    return accounts


def seed_demo_accounts(
    db: Session, auth: FakeAuthAdapter, accounts: list[DemoAccount]
) -> list[str]:
    """Register each account with the fake adapter and make sure its profile row exists."""
    seeded: list[str] = []
    for account in accounts:
        existing = db.scalar(select(User).where(User.email == account.email))
        user_id = existing.id if existing else uuid.uuid4()
        try:
            auth.seed_user(email=account.email, password=account.password, user_id=user_id)
        except ConflictError:
            continue  # already registered in this process
        if existing is None:
            try:
                student_number: str | None = parse_student_email(account.email)
            except BadRequestError:
                student_number = None
            db.add(
                User(
                    id=user_id,
                    email=account.email,
                    first_name="Demo",
                    last_name=account.role.value.title(),
                    student_number=student_number,
                    role=account.role,
                    department="Demo",
                    created_at=datetime.now(timezone.utc),
                )
            )
        elif existing.role is not account.role:
            existing.role = account.role
        seeded.append(f"{account.email} ({account.role.value})")
    db.commit()
    return seeded
