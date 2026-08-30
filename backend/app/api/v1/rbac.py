"""Protected probe endpoints for Role-based authorization checks."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.api.deps import require_admin, require_farmer, require_submitter
from app.models.user import User

router = APIRouter(prefix="/rbac", tags=["rbac"])


class RoleClaimBody(BaseModel):
    """Optional client Role claim — ignored; authorization uses the profile only."""

    model_config = ConfigDict(extra="ignore")

    role: str | None = None


def _probe_payload(user: User) -> dict[str, object]:
    return {"ok": True, "role": user.role.value}


@router.get("/farmer")
def farmer_probe(user: Annotated[User, Depends(require_farmer)]) -> dict[str, object]:
    """Farmer-only probe; Admin succeeds via Admin ⊃ Farmer."""
    return _probe_payload(user)


@router.get("/admin")
def admin_probe(user: Annotated[User, Depends(require_admin)]) -> dict[str, object]:
    """Admin-only probe."""
    return _probe_payload(user)


@router.post("/admin")
def admin_probe_post(
    user: Annotated[User, Depends(require_admin)],
    body: RoleClaimBody = RoleClaimBody(),
) -> dict[str, object]:
    """Admin-only probe that accepts (and ignores) a client Role in the body."""
    del body  # Role claims must never affect authorization.
    return _probe_payload(user)


@router.get("/submit")
def submit_probe(
    user: Annotated[User, Depends(require_submitter)],
) -> dict[str, object]:
    """Submit / Student-capability probe; Farmer and Admin succeed via hierarchy."""
    return _probe_payload(user)
