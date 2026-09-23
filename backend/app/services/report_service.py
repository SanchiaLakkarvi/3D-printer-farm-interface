"""Report service — aggregation logic for the 5 Admin reporting endpoints.

Each public function builds a filtered query on PrintJob, aggregates
metrics, and returns a Pydantic response model ready for JSON serialisation.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.enums import JobStatus, PrinterStatus
from app.models.material import Material
from app.models.print_job import PrintJob
from app.models.printer import Printer
from app.models.user import User
from app.schemas.reports import (
    DepartmentReportItem,
    MaterialReportItem,
    MaterialReportResponse,
    OverallUsageResponse,
    PrinterReportItem,
    StatusBreakdown,
    TimeSeriesPoint,
    UserReportItem,
)


# Statuses that mean a job is "done successfully"
_COMPLETED = frozenset({JobStatus.COMPLETED, JobStatus.READY_FOR_COLLECTION})
# Statuses that mean a job is actively waiting or running
_ACTIVE = frozenset({JobStatus.SUBMITTED, JobStatus.QUEUED, JobStatus.PRINTING})
# "Cancelled" in the UI corresponds to the REMOVED enum value
_CANCELLED = frozenset({JobStatus.REMOVED})


# ---------------------------------------------------------------------------
# Shared filter helper
# ---------------------------------------------------------------------------

def _apply_filters(
    query,
    *,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    printer_id: uuid.UUID | None = None,
    department: str | None = None,
    material_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    status: str | None = None,
):
    """Apply optional query-string filters to a PrintJob SELECT."""
    if from_date is not None:
        query = query.where(PrintJob.submitted_at >= from_date)
    if to_date is not None:
        query = query.where(PrintJob.submitted_at <= to_date)
    if printer_id is not None:
        query = query.where(PrintJob.printer_id == printer_id)
    if department is not None:
        query = query.where(PrintJob.department == department)
    if material_id is not None:
        query = query.where(PrintJob.material_id == material_id)
    if user_id is not None:
        query = query.where(PrintJob.user_id == user_id)
    if status is not None:
        query = query.where(PrintJob.status == status)
    return query


def _load_jobs(
    db: Session,
    *,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    printer_id: uuid.UUID | None = None,
    department: str | None = None,
    material_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    status: str | None = None,
) -> list[PrintJob]:
    """Load PrintJobs with eager-loaded relationships and optional filters."""
    query = (
        select(PrintJob)
        .options(
            joinedload(PrintJob.printer),
            joinedload(PrintJob.material),
            joinedload(PrintJob.user),
        )
    )
    query = _apply_filters(
        query,
        from_date=from_date,
        to_date=to_date,
        printer_id=printer_id,
        department=department,
        material_id=material_id,
        user_id=user_id,
        status=status,
    )
    return list(db.scalars(query).unique())


def _dur(job: PrintJob) -> float:
    """Best-available duration in minutes."""
    return job.actual_duration_min or job.est_duration_min or 0.0


def _fil(job: PrintJob) -> float:
    """Best-available filament in grams."""
    return job.actual_filament_g or job.est_filament_g or 0.0


def _job_date_key(job: PrintJob) -> str:
    """ISO date string from submitted_at for time-series grouping."""
    return job.submitted_at.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Report 1: Overall Farm Usage
# ---------------------------------------------------------------------------

def get_overall_usage(
    db: Session,
    *,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    printer_id: uuid.UUID | None = None,
    department: str | None = None,
    material_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    status: str | None = None,
) -> OverallUsageResponse:
    """Return KPI cards + chart data for the overall farm summary."""
    jobs = _load_jobs(
        db,
        from_date=from_date,
        to_date=to_date,
        printer_id=printer_id,
        department=department,
        material_id=material_id,
        user_id=user_id,
        status=status,
    )

    total = len(jobs)
    completed = sum(1 for j in jobs if j.status in _COMPLETED)
    failed = sum(1 for j in jobs if j.status == JobStatus.FAILED)
    cancelled = sum(1 for j in jobs if j.status in _CANCELLED)
    active_queued = sum(1 for j in jobs if j.status in _ACTIVE)

    success_pct = round((completed / total) * 100, 1) if total > 0 else 0.0

    total_dur_min = sum(_dur(j) for j in jobs)
    total_fil_g = sum(_fil(j) for j in jobs)
    avg_dur = round(total_dur_min / total, 1) if total > 0 else 0.0

    # Chart: Jobs Over Time (line chart — daily counts)
    daily_counts: dict[str, int] = defaultdict(int)
    for j in jobs:
        daily_counts[_job_date_key(j)] += 1
    jobs_over_time = [
        TimeSeriesPoint(date=d, count=c)
        for d, c in sorted(daily_counts.items())
    ]

    # Chart: Job Status Breakdown (donut/pie)
    status_map: dict[str, int] = defaultdict(int)
    for j in jobs:
        label = j.status.value
        # Map to user-friendly labels
        if j.status in _COMPLETED:
            label = "completed"
        elif j.status in _CANCELLED:
            label = "cancelled"
        elif j.status in _ACTIVE:
            label = "active"
        status_map[label] += 1
    status_breakdown = [
        StatusBreakdown(status=s, count=c)
        for s, c in sorted(status_map.items())
    ]

    return OverallUsageResponse(
        total_jobs=total,
        completed_jobs=completed,
        failed_jobs=failed,
        cancelled_jobs=cancelled,
        active_queued_jobs=active_queued,
        success_rate_pct=success_pct,
        total_print_hours=round(total_dur_min / 60.0, 2),
        total_filament_g=round(total_fil_g, 2),
        avg_print_duration_min=avg_dur,
        jobs_over_time=jobs_over_time,
        status_breakdown=status_breakdown,
    )


# ---------------------------------------------------------------------------
# Report 2: Printer Utilization & Hardware
# ---------------------------------------------------------------------------

def get_printer_report(
    db: Session,
    *,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    printer_id: uuid.UUID | None = None,
    department: str | None = None,
    material_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    status: str | None = None,
) -> list[PrinterReportItem]:
    """Return per-printer utilization, failures, and queue length."""
    jobs = _load_jobs(
        db,
        from_date=from_date,
        to_date=to_date,
        printer_id=printer_id,
        department=department,
        material_id=material_id,
        user_id=user_id,
        status=status,
    )
    printers = list(db.scalars(select(Printer)).unique())

    # Total farm hours for utilisation %
    total_farm_min = sum(_dur(j) for j in jobs)
    total_farm_hours = total_farm_min / 60.0 if total_farm_min > 0 else 1.0

    # Live queue counts (unfiltered — always reflect real-time state)
    queue_jobs = list(
        db.scalars(
            select(PrintJob).where(PrintJob.status.in_([
                JobStatus.SUBMITTED, JobStatus.QUEUED, JobStatus.PRINTING,
            ]))
        ).unique()
    )
    queue_by_printer: dict[uuid.UUID | None, int] = defaultdict(int)
    for j in queue_jobs:
        queue_by_printer[j.printer_id] += 1

    result: list[PrinterReportItem] = []
    for p in printers:
        p_jobs = [j for j in jobs if j.printer_id == p.id]
        p_dur_min = sum(_dur(j) for j in p_jobs)
        p_hours = round(p_dur_min / 60.0, 2)
        p_fil_g = round(sum(_fil(j) for j in p_jobs), 2)
        p_completed = sum(1 for j in p_jobs if j.status in _COMPLETED)
        p_failed = sum(1 for j in p_jobs if j.status == JobStatus.FAILED)
        util_pct = round((p_hours / total_farm_hours) * 100, 1) if total_farm_hours > 0 else 0.0

        result.append(PrinterReportItem(
            printer_id=p.id,
            model=p.model,
            location=p.location,
            status=p.status.value,
            total_jobs=len(p_jobs),
            completed_jobs=p_completed,
            failed_jobs=p_failed,
            total_print_hours=p_hours,
            total_filament_g=p_fil_g,
            utilization_pct=util_pct,
            queue_length=queue_by_printer.get(p.id, 0),
        ))

    return result


# ---------------------------------------------------------------------------
# Report 3: Material & Filament Consumption
# ---------------------------------------------------------------------------

def get_material_report(
    db: Session,
    *,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    printer_id: uuid.UUID | None = None,
    department: str | None = None,
    material_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    status: str | None = None,
) -> MaterialReportResponse:
    """Return per-material consumption + filament-usage-over-time series."""
    jobs = _load_jobs(
        db,
        from_date=from_date,
        to_date=to_date,
        printer_id=printer_id,
        department=department,
        material_id=material_id,
        user_id=user_id,
        status=status,
    )
    materials = list(db.scalars(select(Material)).unique())

    items: list[MaterialReportItem] = []
    for m in materials:
        m_jobs = [j for j in jobs if j.material_id == m.id]
        m_fil_g = round(sum(_fil(j) for j in m_jobs), 2)
        items.append(MaterialReportItem(
            material_id=m.id,
            material_name=m.name,
            type=m.type,
            colour=m.colour,
            total_jobs=len(m_jobs),
            total_filament_g=m_fil_g,
        ))

    # Chart: Filament Usage Over Time (daily grams)
    daily_fil: dict[str, float] = defaultdict(float)
    for j in jobs:
        daily_fil[_job_date_key(j)] += _fil(j)
    filament_over_time = [
        TimeSeriesPoint(date=d, count=int(round(g)))
        for d, g in sorted(daily_fil.items())
    ]

    return MaterialReportResponse(
        materials=items,
        filament_over_time=filament_over_time,
    )


# ---------------------------------------------------------------------------
# Report 4: User & Student Usage
# ---------------------------------------------------------------------------

def get_user_report(
    db: Session,
    *,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    printer_id: uuid.UUID | None = None,
    department: str | None = None,
    material_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    status: str | None = None,
) -> list[UserReportItem]:
    """Return per-user/student activity for the searchable table."""
    jobs = _load_jobs(
        db,
        from_date=from_date,
        to_date=to_date,
        printer_id=printer_id,
        department=department,
        material_id=material_id,
        user_id=user_id,
        status=status,
    )

    # Group by user
    user_jobs: dict[uuid.UUID, list[PrintJob]] = defaultdict(list)
    user_map: dict[uuid.UUID, User] = {}
    for j in jobs:
        if j.user is not None:
            user_jobs[j.user_id].append(j)
            user_map[j.user_id] = j.user

    result: list[UserReportItem] = []
    for uid, u_jobs in user_jobs.items():
        user = user_map[uid]
        u_dur_min = sum(_dur(j) for j in u_jobs)
        u_fil_g = sum(_fil(j) for j in u_jobs)
        u_completed = sum(1 for j in u_jobs if j.status in _COMPLETED)
        u_failed = sum(1 for j in u_jobs if j.status == JobStatus.FAILED)

        result.append(UserReportItem(
            user_id=uid,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            student_number=user.student_number,
            department=user.department,
            role=user.role.value,
            total_jobs=len(u_jobs),
            completed_jobs=u_completed,
            failed_jobs=u_failed,
            total_print_hours=round(u_dur_min / 60.0, 2),
            total_filament_g=round(u_fil_g, 2),
        ))

    return result


# ---------------------------------------------------------------------------
# Report 5: Department Usage
# ---------------------------------------------------------------------------

def get_department_report(
    db: Session,
    *,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    printer_id: uuid.UUID | None = None,
    department: str | None = None,
    material_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    status: str | None = None,
) -> list[DepartmentReportItem]:
    """Return per-department aggregation for cost-allocation reporting."""
    jobs = _load_jobs(
        db,
        from_date=from_date,
        to_date=to_date,
        printer_id=printer_id,
        department=department,
        material_id=material_id,
        user_id=user_id,
        status=status,
    )

    dept_data: dict[str, dict] = defaultdict(lambda: {
        "total": 0, "completed": 0, "failed": 0, "dur_min": 0.0, "fil_g": 0.0,
    })

    for j in jobs:
        dept = j.department or "General"
        d = dept_data[dept]
        d["total"] += 1
        d["dur_min"] += _dur(j)
        d["fil_g"] += _fil(j)
        if j.status in _COMPLETED:
            d["completed"] += 1
        if j.status == JobStatus.FAILED:
            d["failed"] += 1

    return [
        DepartmentReportItem(
            department=dept,
            total_jobs=d["total"],
            completed_jobs=d["completed"],
            failed_jobs=d["failed"],
            total_print_hours=round(d["dur_min"] / 60.0, 2),
            total_filament_g=round(d["fil_g"], 2),
        )
        for dept, d in sorted(dept_data.items())
    ]
