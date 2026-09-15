"""Public authentication endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.adapters.auth.port import AuthPort
from app.api.deps import get_auth_port, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    SignInRequest,
    SignInResponse,
    StudentSignupRequest,
    UserProfileResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _profile_response(user: User) -> UserProfileResponse:
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role.value,
        department=user.department,
        student_number=user.student_number,
    )


@router.post(
    "/signup",
    response_model=UserProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def student_signup(
    body: StudentSignupRequest,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthPort, Depends(get_auth_port)],
) -> UserProfileResponse:
    user = auth_service.signup_student(
        db=db,
        auth=auth,
        first_name=body.first_name,
        last_name=body.last_name,
        email=str(body.email),
        password=body.password,
        department=body.department,
    )
    return _profile_response(user)


@router.post("/signin", response_model=SignInResponse)
def signin(
    body: SignInRequest,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthPort, Depends(get_auth_port)],
) -> SignInResponse:
    session, user = auth_service.sign_in(
        db=db,
        auth=auth,
        email=str(body.email),
        password=body.password,
    )
    return SignInResponse(
        access_token=session.access_token,
        user=_profile_response(user),
    )


@router.get("/me", response_model=UserProfileResponse)
def me(user: Annotated[User, Depends(get_current_user)]) -> UserProfileResponse:
    return _profile_response(user)


@router.post("/signout", status_code=status.HTTP_204_NO_CONTENT)
def signout() -> None:
    """Client-side Sign-out: discard the access token locally.

    Supabase access tokens are JWTs; the API does not maintain a server-side
    session store. Clients must delete the stored token. Optional future work:
    call Supabase logout / revoke if refresh-token flows are added.
    """
    return None
