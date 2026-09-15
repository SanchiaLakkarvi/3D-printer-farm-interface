"""Printer service — database operations for printers."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import NotFoundError
from app.models.material import Material
from app.models.printer import Printer
from app.schemas.printer import PrinterCreate, PrinterUpdate


def list_printers(db: Session) -> list[Printer]:
    """Return all printers with eager-loaded current material."""
    return list(
        db.scalars(
            select(Printer)
            .options(joinedload(Printer.current_material))
            .order_by(Printer.model)
        ).unique()
    )


def get_printer(db: Session, printer_id: uuid.UUID) -> Printer:
    """Return one printer or raise 404."""
    printer = db.scalars(
        select(Printer)
        .options(joinedload(Printer.current_material))
        .where(Printer.id == printer_id)
    ).unique().first()
    if printer is None:
        raise NotFoundError("Printer", str(printer_id))
    return printer


def create_printer(db: Session, data: PrinterCreate) -> Printer:
    """Create a new printer and return it with material loaded."""
    if data.current_material_id is not None:
        _validate_material_exists(db, data.current_material_id)

    printer = Printer(
        id=uuid.uuid4(),
        model=data.model,
        status=data.status,
        bed_size=data.bed_size,
        location=data.location,
        locked_profile=data.locked_profile,
        current_material_id=data.current_material_id,
    )
    db.add(printer)
    db.commit()
    db.refresh(printer)
    return get_printer(db, printer.id)


def update_printer(
    db: Session, printer_id: uuid.UUID, data: PrinterUpdate,
) -> Printer:
    """Update printer fields and return it with material loaded."""
    printer = get_printer(db, printer_id)
    update_data = data.model_dump(exclude_unset=True)

    if "current_material_id" in update_data and update_data["current_material_id"] is not None:
        _validate_material_exists(db, update_data["current_material_id"])

    for field, value in update_data.items():
        setattr(printer, field, value)

    db.commit()
    db.refresh(printer)
    return get_printer(db, printer.id)


def _validate_material_exists(db: Session, material_id: uuid.UUID) -> None:
    """Raise 404 if material does not exist."""
    material = db.get(Material, material_id)
    if material is None:
        raise NotFoundError("Material", str(material_id))
