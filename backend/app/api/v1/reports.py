"""Farm Statistics & Usage Reporting API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_farmer
from app.db.session import get_db
from app.models.user import User
from app.schemas.jobs import FarmStatisticsResponse
from app.services import job_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/statistics", response_model=FarmStatisticsResponse)
def get_farm_statistics(
    _staff: Annotated[User, Depends(require_farmer)],
    db: Annotated[Session, Depends(get_db)],
) -> FarmStatisticsResponse:
    """Return overall farm usage statistics, revenue, printer utilization, and department analytics. Farmer/Admin only."""
    return job_service.get_farm_statistics(db=db)
