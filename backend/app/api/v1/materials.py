"""Material API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.material import MaterialCreate, MaterialOut
from app.services import material_service

router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("", response_model=list[MaterialOut])
def list_materials(
    _current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[MaterialOut]:
    """List all materials. Requires authentication."""
    materials = material_service.list_materials(db)
    return [MaterialOut.model_validate(m) for m in materials]


@router.post("", response_model=MaterialOut, status_code=201)
def create_material(
    body: MaterialCreate,
    _admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> MaterialOut:
    """Create a new material. Admin only."""
    material = material_service.create_material(db, body)
    return MaterialOut.model_validate(material)
