from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import JobStatus, job_status_enum

if TYPE_CHECKING:
    from app.models.collection_record import CollectionRecord
    from app.models.job_validation import JobValidation
    from app.models.material import Material
    from app.models.notification import Notification
    from app.models.printer import Printer
    from app.models.user import User


class PrintJob(Base):
    __tablename__ = "print_jobs"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="print_jobs_pkey"),
        Index("idx_print_jobs_user_id", "user_id"),
        Index("idx_print_jobs_printer_id", "printer_id"),
        Index("idx_print_jobs_status", "status"),
        Index("idx_print_jobs_material_id", "material_id"),
        Index(
            "idx_print_jobs_queue_submitted_at",
            "submitted_at",
            postgresql_where=text("status IN ('submitted', 'queued')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", name="print_jobs_user_id_fkey"),
        nullable=False,
    )
    printer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("printers.id", name="print_jobs_printer_id_fkey"),
        nullable=True,
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("materials.id", name="print_jobs_material_id_fkey"),
        nullable=False,
    )
    gcode_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        job_status_enum,
        nullable=False,
        server_default=text("'submitted'::job_status"),
    )
    est_duration_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_filament_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_duration_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_filament_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    department: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship(back_populates="print_jobs")
    printer: Mapped[Printer | None] = relationship(back_populates="print_jobs")
    material: Mapped[Material] = relationship(back_populates="print_jobs")
    validations: Mapped[list[JobValidation]] = relationship(back_populates="job")
    notifications: Mapped[list[Notification]] = relationship(back_populates="job")
    collection_record: Mapped[CollectionRecord | None] = relationship(
        back_populates="job",
        uselist=False,
    )
