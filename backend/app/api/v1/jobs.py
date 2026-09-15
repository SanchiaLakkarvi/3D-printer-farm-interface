"""Print Queue & History API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.jobs import PrintHistoryResponse, QueueTileResponse
from app.services import job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/queue", response_model=list[QueueTileResponse])
def get_print_queue(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[QueueTileResponse]:
    """List active print queue & completion tiles with timing estimates. Requires authentication."""
    return job_service.get_print_queue(db=db, user=current_user)


@router.get("/history", response_model=list[PrintHistoryResponse])
def get_print_history(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[PrintHistoryResponse]:
    """List print history with calculated statistics and cost ($2 1st hr + $0.50 addl hrs). Requires authentication."""
    return job_service.get_print_history(db=db, user=current_user)
