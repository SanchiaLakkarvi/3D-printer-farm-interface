"""Job service — business logic for Print Queue timing estimates, Print History, and Farm Statistics."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.enums import JobStatus, UserRole
from app.models.material import Material
from app.models.print_job import PrintJob
from app.models.printer import Printer
from app.models.user import User
from app.schemas.jobs import (
    DepartmentUtilStat,
    FarmStatisticsResponse,
    MaterialUtilStat,
    PrintHistoryResponse,
    PrinterAssignedSummary,
    PrinterUtilStat,
    QueueTileResponse,
)
from app.services.pricing_service import calculate_print_cost


def _format_duration(duration_min: float | None) -> str:
    """Format duration in minutes into human-readable string e.g. '1h 45m' or '30m'."""
    if duration_min is None or duration_min <= 0:
        return "0m"
    hours = int(duration_min // 60)
    mins = int(round(duration_min % 60))
    if hours > 0 and mins > 0:
        return f"{hours}h {mins}m"
    elif hours > 0:
        return f"{hours}h"
    else:
        return f"{mins}m"


def _make_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def get_print_queue(db: Session, user: User | None = None) -> list[QueueTileResponse]:
    """Return active queue and completion tiles with estimated start/completion times."""
    query = (
        select(PrintJob)
        .options(
            joinedload(PrintJob.printer).joinedload(Printer.current_material),
            joinedload(PrintJob.material),
        )
        .where(
            PrintJob.status.in_(
                [JobStatus.SUBMITTED, JobStatus.QUEUED, JobStatus.PRINTING]
            )
        )
        .order_by(PrintJob.submitted_at.asc())
    )

    if user is not None and user.role == UserRole.STUDENT:
        query = query.where(PrintJob.user_id == user.id)

    jobs = list(db.scalars(query).unique())
    now = datetime.now(timezone.utc)
    cumulative_wait_minutes = 0.0

    responses: list[QueueTileResponse] = []
    for job in jobs:
        est_min = job.est_duration_min or 30.0

        if job.status == JobStatus.PRINTING:
            est_start = _make_aware(job.submitted_at)
            est_completion = est_start + timedelta(minutes=est_min)
            if est_completion < now:
                est_completion = now + timedelta(minutes=5)
        else:
            est_start = now + timedelta(minutes=cumulative_wait_minutes)
            est_completion = est_start + timedelta(minutes=est_min)
            cumulative_wait_minutes += est_min

        printer_summary = None
        if job.printer is not None:
            printer_summary = PrinterAssignedSummary(
                id=job.printer.id,
                model=job.printer.model,
                location=job.printer.location,
                status=job.printer.status,
            )

        filename = os.path.basename(job.gcode_path) if job.gcode_path else "print_job.gcode"

        responses.append(
            QueueTileResponse(
                job_id=job.id,
                filename=filename,
                status=job.status,
                assigned_printer=printer_summary,
                est_duration_min=job.est_duration_min,
                est_duration_formatted=_format_duration(job.est_duration_min),
                est_start_time=est_start,
                est_completion_time=est_completion,
                submitted_at=job.submitted_at,
            )
        )

    return responses


def get_print_history(db: Session, user: User) -> list[PrintHistoryResponse]:
    """Return print history statistics without serving full G-code files."""
    query = (
        select(PrintJob)
        .options(
            joinedload(PrintJob.printer),
            joinedload(PrintJob.material),
        )
        .where(
            PrintJob.status.in_(
                [
                    JobStatus.COMPLETED,
                    JobStatus.FAILED,
                    JobStatus.READY_FOR_COLLECTION,
                    JobStatus.REMOVED,
                ]
            )
        )
        .order_by(PrintJob.submitted_at.desc())
    )

    if user.role == UserRole.STUDENT:
        query = query.where(PrintJob.user_id == user.id)

    jobs = list(db.scalars(query).unique())
    responses: list[PrintHistoryResponse] = []

    for job in jobs:
        dur = job.actual_duration_min or job.est_duration_min or 0.0
        cost = calculate_print_cost(dur)
        filename = os.path.basename(job.gcode_path) if job.gcode_path else "print_job.gcode"

        responses.append(
            PrintHistoryResponse(
                job_id=job.id,
                filename=filename,
                status=job.status,
                material_name=job.material.name if job.material else None,
                material_type=job.material.type if job.material else None,
                colour=job.material.colour if job.material else None,
                printer_model=job.printer.model if job.printer else None,
                printer_location=job.printer.location if job.printer else None,
                department=job.department,
                est_duration_min=job.est_duration_min,
                actual_duration_min=job.actual_duration_min,
                est_filament_g=job.est_filament_g,
                actual_filament_g=job.actual_filament_g,
                calculated_cost_usd=cost,
                submitted_at=job.submitted_at,
                completed_at=job.completed_at,
            )
        )

    return responses


def get_farm_statistics(db: Session) -> FarmStatisticsResponse:
    """Return overall farm usage, revenue, hardware utilization, and department analytics."""
    all_jobs = list(
        db.scalars(
            select(PrintJob).options(
                joinedload(PrintJob.printer),
                joinedload(PrintJob.material),
            )
        ).unique()
    )

    total_jobs = len(all_jobs)
    completed_jobs = sum(
        1 for j in all_jobs if j.status in (JobStatus.COMPLETED, JobStatus.READY_FOR_COLLECTION, JobStatus.REMOVED)
    )
    failed_jobs = sum(1 for j in all_jobs if j.status == JobStatus.FAILED)
    active_queued_jobs = sum(
        1 for j in all_jobs if j.status in (JobStatus.SUBMITTED, JobStatus.QUEUED, JobStatus.PRINTING)
    )

    total_revenue = 0.0
    total_print_time_min = 0.0
    total_filament_g = 0.0

    dept_revenue: dict[str, float] = {}
    dept_jobs: dict[str, int] = {}

    for j in all_jobs:
        dur = j.actual_duration_min or j.est_duration_min or 0.0
        fil = j.actual_filament_g or j.est_filament_g or 0.0
        total_print_time_min += dur
        total_filament_g += fil

        if j.status in (JobStatus.COMPLETED, JobStatus.READY_FOR_COLLECTION, JobStatus.REMOVED):
            cost = calculate_print_cost(dur)
            total_revenue += cost
            dept = j.department or "General"
            dept_revenue[dept] = dept_revenue.get(dept, 0.0) + cost
            dept_jobs[dept] = dept_jobs.get(dept, 0) + 1

    # Per-printer utilization
    printers = list(db.scalars(select(Printer)).unique())
    printer_stats: list[PrinterUtilStat] = []
    total_hours_sum = total_print_time_min / 60.0 if total_print_time_min > 0 else 1.0

    for p in printers:
        p_jobs = [j for j in all_jobs if j.printer_id == p.id]
        p_jobs_count = len(p_jobs)
        p_dur_min = sum(j.actual_duration_min or j.est_duration_min or 0.0 for j in p_jobs)
        p_hours = round(p_dur_min / 60.0, 2)
        util_pct = round((p_hours / total_hours_sum) * 100.0, 1) if total_hours_sum > 0 else 0.0

        printer_stats.append(
            PrinterUtilStat(
                printer_id=p.id,
                model=p.model,
                location=p.location,
                total_jobs=p_jobs_count,
                total_hours=p_hours,
                utilization_pct=util_pct,
            )
        )

    # Per-material utilization
    materials = list(db.scalars(select(Material)).unique())
    material_stats: list[MaterialUtilStat] = []

    for m in materials:
        m_jobs = [j for j in all_jobs if j.material_id == m.id]
        m_jobs_count = len(m_jobs)
        m_fil_g = sum(j.actual_filament_g or j.est_filament_g or 0.0 for j in m_jobs)

        material_stats.append(
            MaterialUtilStat(
                material_id=m.id,
                material_name=m.name,
                type=m.type,
                total_jobs=m_jobs_count,
                total_filament_g=round(m_fil_g, 2),
            )
        )

    # Department breakdown
    department_stats: list[DepartmentUtilStat] = [
        DepartmentUtilStat(
            department=dept,
            total_jobs=dept_jobs.get(dept, 0),
            total_revenue_usd=round(rev, 2),
        )
        for dept, rev in dept_revenue.items()
    ]

    return FarmStatisticsResponse(
        total_jobs=total_jobs,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        active_queued_jobs=active_queued_jobs,
        total_revenue_usd=round(total_revenue, 2),
        total_print_time_hours=round(total_print_time_min / 60.0, 2),
        total_filament_consumed_g=round(total_filament_g, 2),
        printer_stats=printer_stats,
        material_stats=material_stats,
        department_stats=department_stats,
    )
