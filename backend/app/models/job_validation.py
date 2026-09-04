from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, PrimaryKeyConstraint, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CheckType, check_type_enum

if TYPE_CHECKING:
    from app.models.print_job import PrintJob


class JobValidation(Base):
    __tablename__ = "job_validations"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="job_validations_pkey"),
        Index("idx_job_validations_job_id", "job_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        server_default=text("gen_random_uuid()"),
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("print_jobs.id", name="job_validations_job_id_fkey"),
        nullable=False,
    )
    check_type: Mapped[CheckType] = mapped_column(check_type_enum, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    job: Mapped[PrintJob] = relationship(back_populates="validations")
