from __future__ import annotations

from app.schemas.auth import (
    SignInRequest,
    SignInResponse,
    StudentSignupRequest,
    UserProfileResponse,
)
from app.schemas.material import MaterialCreate, MaterialOut
from app.schemas.printer import PrinterCreate, PrinterOut, PrinterUpdate

__all__ = [
    "MaterialCreate",
    "MaterialOut",
    "PrinterCreate",
    "PrinterOut",
    "PrinterUpdate",
    "SignInRequest",
    "SignInResponse",
    "StudentSignupRequest",
    "UserProfileResponse",
]
