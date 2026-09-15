"""FastAPI dependencies for Auth and the current User profile."""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.adapters.auth.fake import FakeAuthAdapter
from app.adapters.auth.port import AuthPort
from app.adapters.auth.supabase import SupabaseAuthAdapter
from app.core.config import settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.services import auth_service

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def _build_auth_port() -> AuthPort:
    if settings.auth_adapter == "fake":
        return FakeAuthAdapter()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required "
            "when AUTH_ADAPTER=supabase"
        )
    return SupabaseAuthAdapter(
        base_url=settings.supabase_url,
        service_role_key=settings.supabase_service_role_key,
        anon_key=settings.supabase_anon_key,
    )


def get_auth_port() -> AuthPort:
    return _build_auth_port()


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthPort, Depends(get_auth_port)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Missing bearer token")
    return auth_service.get_profile_for_token(
        db=db,
        auth=auth,
        token=credentials.credentials,
    )


def require_roles(*allowed: UserRole) -> Callable[..., User]:
    """Dependency factory: allow listed Roles.

    Capability hierarchy on the same profile: Admin ⊃ Farmer ⊃ submit (student).
    """

    allowed_set = set(allowed)

    def _dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role in allowed_set:
            return user
        if user.role == UserRole.ADMIN and (
            UserRole.FARMER in allowed_set or UserRole.STUDENT in allowed_set
        ):
            return user
        if user.role == UserRole.FARMER and UserRole.STUDENT in allowed_set:
            return user
        raise ForbiddenError()

    return _dependency


require_farmer = require_roles(UserRole.FARMER)
require_admin = require_roles(UserRole.ADMIN)
require_submitter = require_roles(UserRole.STUDENT)
