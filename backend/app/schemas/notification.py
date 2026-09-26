"""Pydantic schemas for Notification API responses."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import NotificationType


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID | None
    type: NotificationType
    message: str
    is_read: bool
    sent_at: datetime


class UnreadCountOut(BaseModel):
    count: int
