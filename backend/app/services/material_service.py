"""Material service — database operations for materials."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.material import Material
from app.schemas.material import MaterialCreate


def list_materials(db: Session) -> list[Material]:
    """Return all materials ordered by name."""
    return list(db.scalars(select(Material).order_by(Material.name)))


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
