"""Printer API endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.printer import PrinterCreate, PrinterOut, PrinterUpdate
from app.services import printer_service

router = APIRouter(prefix="/printers", tags=["printers"])


@router.get("", response_model=list[PrinterOut])
def list_printers(
    _current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[PrinterOut]:
    """List all printers with current material. Requires authentication."""
    printers = printer_service.list_printers(db)
    return [PrinterOut.model_validate(p) for p in printers]


@router.get("/{printer_id}", response_model=PrinterOut)
def get_printer(
    printer_id: uuid.UUID,
    _current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PrinterOut:
    """Get a single printer by ID. Requires authentication."""
    printer = printer_service.get_printer(db, printer_id)
    return PrinterOut.model_validate(printer)


@router.post("", response_model=PrinterOut, status_code=201)
def create_printer(
    body: PrinterCreate,
    _admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> PrinterOut:
    """Create a new printer. Admin only."""
    printer = printer_service.create_printer(db, body)
    return PrinterOut.model_validate(printer)


@router.patch("/{printer_id}", response_model=PrinterOut)
def update_printer(
    printer_id: uuid.UUID,
    body: PrinterUpdate,
    _admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> PrinterOut:
    """Update printer status, material, location, or locked profile. Admin only."""
    printer = printer_service.update_printer(db, printer_id, body)
    return PrinterOut.model_validate(printer)
