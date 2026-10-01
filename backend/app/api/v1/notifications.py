"""Notification API endpoints — the signed-in user's own notifications."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import NotificationOut, UnreadCountOut
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    unread: bool = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[NotificationOut]:
    """List your notifications, newest first. `unread=true` returns only unread ones."""
    items = notification_service.list_notifications(db, current_user, unread, limit)
    return [NotificationOut.model_validate(n) for n in items]


@router.get("/unread-count", response_model=UnreadCountOut)
def get_unread_count(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UnreadCountOut:
    """Number of unread notifications, for the header badge."""
    return UnreadCountOut(count=notification_service.unread_count(db, current_user))


@router.post("/read-all", response_model=UnreadCountOut)
def mark_all_read(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UnreadCountOut:
    """Mark all your notifications read. Returns the unread count afterwards (0)."""
    notification_service.mark_all_read(db, current_user)
    return UnreadCountOut(count=0)


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NotificationOut:
    """Mark one of your notifications read. Someone else's notification returns 404."""
    notification = notification_service.mark_read(db, current_user, notification_id)
    return NotificationOut.model_validate(notification)
