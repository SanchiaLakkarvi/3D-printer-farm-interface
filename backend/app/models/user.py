from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, PrimaryKeyConstraint, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UserRole, user_role_enum

if TYPE_CHECKING:
    from app.models.collection_record import CollectionRecord
    from app.models.maintenance_log import MaintenanceLog
    from app.models.notification import Notification
    from app.models.print_job import PrintJob


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="users_pkey"),
        UniqueConstraint("email", name="users_email_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(Text, nullable=False)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    student_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[UserRole] = mapped_column(
        user_role_enum,
        nullable=False,
        server_default=text("'student'::user_role"),
    )
    department: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    print_jobs: Mapped[list[PrintJob]] = relationship(back_populates="user")
    notifications: Mapped[list[Notification]] = relationship(back_populates="user")
    collection_records: Mapped[list[CollectionRecord]] = relationship(
        back_populates="farmer",
    )
    maintenance_logs: Mapped[list[MaintenanceLog]] = relationship(
        back_populates="farmer",
    )
