"""Pydantic schemas for Printer API requests and responses."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import PrinterStatus
from app.schemas.material import MaterialOut


class PrinterCreate(BaseModel):
    model: str
    bed_size: str
    location: str
    status: PrinterStatus = PrinterStatus.IDLE
    locked_profile: dict[str, Any] | None = None
    current_material_id: uuid.UUID | None = None


class PrinterUpdate(BaseModel):
    status: PrinterStatus | None = None
    location: str | None = None
    locked_profile: dict[str, Any] | None = None
    current_material_id: uuid.UUID | None = None


class PrinterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    model: str
    status: PrinterStatus
    bed_size: str
    location: str
    locked_profile: dict[str, Any] | None = None
    current_material: MaterialOut | None = None
