from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.print_job import PrintJob
    from app.models.user import User


class CollectionRecord(Base):
    __tablename__ = "collection_records"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="collection_records_pkey"),
        UniqueConstraint("job_id", name="collection_records_job_id_key"),
        # Redundant with the unique constraint; kept to match live Supabase.
        Index("idx_collection_records_job_id", "job_id"),
        Index("idx_collection_records_farmer_id", "farmer_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        server_default=text("gen_random_uuid()"),
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("print_jobs.id", name="collection_records_job_id_fkey"),
        nullable=False,
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", name="collection_records_farmer_id_fkey"),
        nullable=False,
    )
    ready_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    removed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    collected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped[PrintJob] = relationship(back_populates="collection_record")
    farmer: Mapped[User] = relationship(back_populates="collection_records")
