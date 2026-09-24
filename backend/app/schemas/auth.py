from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StudentSignupRequest(BaseModel):
    """Public Student Sign-up payload. Role is never accepted from the client."""

    model_config = ConfigDict(extra="ignore")

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    department: str = Field(min_length=1, max_length=100)


class SignInRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)
    # Client Role claims are ignored if present (extra="ignore").


class SignupPendingResponse(BaseModel):
    """Student Sign-up accepted; confirm email before Sign-in creates the profile."""

    message: str
    email: str


class ConfirmEmailRequest(BaseModel):
    """Explicit email confirmation (button click), not mail-scanner GET prefetch."""

    model_config = ConfigDict(extra="ignore")

    token_hash: str = Field(min_length=8, max_length=512)
    type: str = Field(default="signup", min_length=1, max_length=32)


class ConfirmEmailResponse(BaseModel):
    message: str


class VerifySignupCodeRequest(BaseModel):
    """Confirm signup with the emailed 6-digit OTP (primary path)."""

    model_config = ConfigDict(extra="ignore")

    email: str = Field(min_length=3, max_length=254)
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class ResendSignupCodeRequest(BaseModel):
    """Resend the signup confirmation OTP email."""

    model_config = ConfigDict(extra="ignore")

    email: str = Field(min_length=3, max_length=254)


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    first_name: str
    last_name: str
    role: str
    department: str | None
    student_number: str | None


class SignInResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse
