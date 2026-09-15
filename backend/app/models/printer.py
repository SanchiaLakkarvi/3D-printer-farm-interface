from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, PrimaryKeyConstraint, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PrinterStatus, printer_status_enum

if TYPE_CHECKING:
    from app.models.maintenance_log import MaintenanceLog
    from app.models.material import Material
    from app.models.print_job import PrintJob


class Printer(Base):
    __tablename__ = "printers"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="printers_pkey"),
        Index("idx_printers_current_material_id", "current_material_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        server_default=text("gen_random_uuid()"),
    )
    model: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[PrinterStatus] = mapped_column(
        printer_status_enum,
        nullable=False,
        server_default=text("'idle'::printer_status"),
    )
    bed_size: Mapped[str] = mapped_column(Text, nullable=False)
    locked_profile: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    current_material_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("materials.id", name="printers_current_material_id_fkey"),
        nullable=True,
    )
    location: Mapped[str] = mapped_column(Text, nullable=False)

    current_material: Mapped[Material | None] = relationship(back_populates="printers")
    print_jobs: Mapped[list[PrintJob]] = relationship(back_populates="printer")
    maintenance_logs: Mapped[list[MaintenanceLog]] = relationship(
        back_populates="printer",
    )
