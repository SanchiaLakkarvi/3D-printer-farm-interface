from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, PrimaryKeyConstraint, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.printer import Printer
    from app.models.user import User


class MaintenanceLog(Base):
    __tablename__ = "maintenance_logs"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="maintenance_logs_pkey"),
        Index("idx_maintenance_logs_printer_id", "printer_id"),
        Index("idx_maintenance_logs_farmer_id", "farmer_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        server_default=text("gen_random_uuid()"),
    )
    printer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("printers.id", name="maintenance_logs_printer_id_fkey"),
        nullable=False,
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", name="maintenance_logs_farmer_id_fkey"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    printer: Mapped[Printer] = relationship(back_populates="maintenance_logs")
    farmer: Mapped[User] = relationship(back_populates="maintenance_logs")
