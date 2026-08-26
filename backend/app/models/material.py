from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import PrimaryKeyConstraint, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.print_job import PrintJob
    from app.models.printer import Printer


class Material(Base):
    __tablename__ = "materials"
    __table_args__ = (PrimaryKeyConstraint("id", name="materials_pkey"),)

    id: Mapped[uuid.UUID] = mapped_column(
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    colour: Mapped[str] = mapped_column(Text, nullable=False)

    printers: Mapped[list[Printer]] = relationship(back_populates="current_material")
    print_jobs: Mapped[list[PrintJob]] = relationship(back_populates="material")
