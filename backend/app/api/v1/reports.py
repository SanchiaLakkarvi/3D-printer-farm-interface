"""Admin Usage Reporting API endpoints.

5 dedicated reporting endpoints for the Admin dashboard, plus the
legacy /statistics endpoint kept for backward compatibility.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_farmer
from app.db.session import get_db
from app.models.user import User
from app.schemas.jobs import FarmStatisticsResponse
from app.schemas.reports import (
    DepartmentReportItem,
    MaterialReportResponse,
    OverallUsageResponse,
    PrinterReportItem,
    UserReportItem,
)
from app.services import job_service, report_service

router = APIRouter(prefix="/reports", tags=["reports"])


# ---------------------------------------------------------------------------
# Report 1: Overall Farm Usage
# ---------------------------------------------------------------------------

@router.get("/usage", response_model=OverallUsageResponse)
def get_usage_report(
    _staff: Annotated[User, Depends(require_farmer)],
    db: Annotated[Session, Depends(get_db)],
    from_date: Annotated[datetime | None, Query(alias="from_date")] = None,
    to_date: Annotated[datetime | None, Query(alias="to_date")] = None,
    printer_id: Annotated[uuid.UUID | None, Query()] = None,
    department: Annotated[str | None, Query()] = None,
    material_id: Annotated[uuid.UUID | None, Query()] = None,
    user_id: Annotated[uuid.UUID | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
) -> OverallUsageResponse:
    """Overall farm KPIs, Jobs Over Time chart, and Job Status Breakdown chart. Farmer/Admin only."""
    return report_service.get_overall_usage(
        db,
        from_date=from_date,
        to_date=to_date,
        printer_id=printer_id,
        department=department,
        material_id=material_id,
        user_id=user_id,
        status=status,
    )


# ---------------------------------------------------------------------------
# Report 2: Printer Utilization & Hardware
# ---------------------------------------------------------------------------

@router.get("/printers", response_model=list[PrinterReportItem])
def get_printer_report(
    _staff: Annotated[User, Depends(require_farmer)],
    db: Annotated[Session, Depends(get_db)],
    from_date: Annotated[datetime | None, Query(alias="from_date")] = None,
    to_date: Annotated[datetime | None, Query(alias="to_date")] = None,
    printer_id: Annotated[uuid.UUID | None, Query()] = None,
    department: Annotated[str | None, Query()] = None,
    material_id: Annotated[uuid.UUID | None, Query()] = None,
    user_id: Annotated[uuid.UUID | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
) -> list[PrinterReportItem]:
    """Per-printer utilization, failure rates, and queue lengths. Farmer/Admin only."""
    return report_service.get_printer_report(
        db,
        from_date=from_date,
        to_date=to_date,
        printer_id=printer_id,
        department=department,
        material_id=material_id,
        user_id=user_id,
        status=status,
    )


# ---------------------------------------------------------------------------
# Report 3: Material & Filament Consumption
# ---------------------------------------------------------------------------

@router.get("/materials", response_model=MaterialReportResponse)
def get_material_report(
    _staff: Annotated[User, Depends(require_farmer)],
    db: Annotated[Session, Depends(get_db)],
    from_date: Annotated[datetime | None, Query(alias="from_date")] = None,
    to_date: Annotated[datetime | None, Query(alias="to_date")] = None,
    printer_id: Annotated[uuid.UUID | None, Query()] = None,
    department: Annotated[str | None, Query()] = None,
    material_id: Annotated[uuid.UUID | None, Query()] = None,
    user_id: Annotated[uuid.UUID | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
) -> MaterialReportResponse:
    """Per-material filament consumption and usage-over-time series. Farmer/Admin only."""
    return report_service.get_material_report(
        db,
        from_date=from_date,
        to_date=to_date,
        printer_id=printer_id,
        department=department,
        material_id=material_id,
        user_id=user_id,
        status=status,
    )


# ---------------------------------------------------------------------------
# Report 4: User & Student Usage
# ---------------------------------------------------------------------------

@router.get("/users", response_model=list[UserReportItem])
def get_user_report(
    _staff: Annotated[User, Depends(require_farmer)],
    db: Annotated[Session, Depends(get_db)],
    from_date: Annotated[datetime | None, Query(alias="from_date")] = None,
    to_date: Annotated[datetime | None, Query(alias="to_date")] = None,
    printer_id: Annotated[uuid.UUID | None, Query()] = None,
    department: Annotated[str | None, Query()] = None,
    material_id: Annotated[uuid.UUID | None, Query()] = None,
    user_id: Annotated[uuid.UUID | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
) -> list[UserReportItem]:
    """Per-user/student activity for searchable/sortable table. Farmer/Admin only."""
    return report_service.get_user_report(
        db,
        from_date=from_date,
        to_date=to_date,
        printer_id=printer_id,
        department=department,
        material_id=material_id,
        user_id=user_id,
        status=status,
    )


# ---------------------------------------------------------------------------
# Report 5: Department Usage
# ---------------------------------------------------------------------------

@router.get("/departments", response_model=list[DepartmentReportItem])
def get_department_report(
    _staff: Annotated[User, Depends(require_farmer)],
    db: Annotated[Session, Depends(get_db)],
    from_date: Annotated[datetime | None, Query(alias="from_date")] = None,
    to_date: Annotated[datetime | None, Query(alias="to_date")] = None,
    printer_id: Annotated[uuid.UUID | None, Query()] = None,
    department: Annotated[str | None, Query()] = None,
    material_id: Annotated[uuid.UUID | None, Query()] = None,
    user_id: Annotated[uuid.UUID | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
) -> list[DepartmentReportItem]:
    """Per-department cost-allocation and usage breakdown. Farmer/Admin only."""
    return report_service.get_department_report(
        db,
        from_date=from_date,
        to_date=to_date,
        printer_id=printer_id,
        department=department,
        material_id=material_id,
        user_id=user_id,
        status=status,
    )


# ---------------------------------------------------------------------------
# Legacy endpoint (backward compatibility)
# ---------------------------------------------------------------------------

@router.get("/statistics", response_model=FarmStatisticsResponse, deprecated=True)
def get_farm_statistics(
    _staff: Annotated[User, Depends(require_farmer)],
    db: Annotated[Session, Depends(get_db)],
) -> FarmStatisticsResponse:
    """[DEPRECATED] Use /api/reports/usage instead. Returns overall farm stats."""
    return job_service.get_farm_statistics(db=db)
