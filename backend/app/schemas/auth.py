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
