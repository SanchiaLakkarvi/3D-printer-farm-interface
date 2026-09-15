"""Material service — database operations for materials."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.material import Material
from app.schemas.material import MaterialCreate, MaterialUpdate


def list_materials(db: Session) -> list[Material]:
    """Return all materials ordered by name."""
    return list(db.scalars(select(Material).order_by(Material.name)))


def get_material(db: Session, material_id: uuid.UUID) -> Material:
    """Return one material by ID or raise 404."""
    material = db.get(Material, material_id)
    if material is None:
        raise NotFoundError("Material", str(material_id))
    return material


def create_material(db: Session, data: MaterialCreate) -> Material:
    """Create a new material and return it."""
    material = Material(
        id=uuid.uuid4(),
        name=data.name,
        type=data.type,
        colour=data.colour,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def update_material(
    db: Session, material_id: uuid.UUID, data: MaterialUpdate,
) -> Material:
    """Update material fields and return updated material."""
    material = get_material(db, material_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(material, field, value)
    db.commit()
    db.refresh(material)
    return material
