from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, PrimaryKeyConstraint, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import NotificationType, notification_type_enum

if TYPE_CHECKING:
    from app.models.print_job import PrintJob
    from app.models.user import User


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="notifications_pkey"),
        Index("idx_notifications_user_id", "user_id"),
        Index("idx_notifications_user_is_read", "user_id", "is_read"),
        Index("idx_notifications_job_id", "job_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", name="notifications_user_id_fkey"),
        nullable=False,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("print_jobs.id", name="notifications_job_id_fkey"),
        nullable=True,
    )
    type: Mapped[NotificationType] = mapped_column(
        notification_type_enum,
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    user: Mapped[User] = relationship(back_populates="notifications")
    job: Mapped[PrintJob | None] = relationship(back_populates="notifications")
