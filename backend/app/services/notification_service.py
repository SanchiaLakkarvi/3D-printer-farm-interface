"""Notification service — a user's own in-app notifications.

Notifications are written by the printer sync loop; this module only reads them
and tracks read state. Every query is scoped to the requesting user.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.notification import Notification
from app.models.user import User


def list_notifications(db: Session, user: User, unread_only: bool, limit: int) -> list[Notification]:
    """Return the user's notifications, newest first."""
    query = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        query = query.where(Notification.is_read.is_(False))
    query = query.order_by(Notification.sent_at.desc()).limit(limit)
    return list(db.scalars(query))


def unread_count(db: Session, user: User) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
    ) or 0


def mark_read(db: Session, user: User, notification_id: uuid.UUID) -> Notification:
    """Mark one of the user's notifications read. Another user's id is a 404, not a 403."""
    notification = db.get(Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise NotFoundError("Notification", str(notification_id))
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_read(db: Session, user: User) -> int:
    """Mark all of the user's notifications read; returns how many changed."""
    result = db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    db.commit()
    return result.rowcount or 0
