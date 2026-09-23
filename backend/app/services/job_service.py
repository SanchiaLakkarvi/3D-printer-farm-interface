"""Job service — business logic for Print Queue timing estimates, Print History, and Farm Statistics."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.enums import JobStatus, PrinterStatus, UserRole
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


DEFAULT_DURATION_MIN = 30.0
OVERRUN_GRACE_MIN = 5.0
_UNASSIGNABLE_STATUSES = frozenset(
    {PrinterStatus.ERROR, PrinterStatus.OFFLINE, PrinterStatus.MAINTENANCE}
)


def _duration_of(job: PrintJob) -> float:
    return job.est_duration_min if job.est_duration_min else DEFAULT_DURATION_MIN


def compute_queue_schedule(
    jobs: list[PrintJob],
    printers: list[Printer],
    now: datetime,
) -> dict[uuid.UUID, tuple[datetime, datetime, uuid.UUID | None]]:
    """Estimate (start, completion, printer) for every active job, per printer.

    Printing jobs run from their real start. Waiting jobs are first-come,
    first-served: a job with a printer follows that printer's queue, and an
    unassigned job takes whichever available printer frees up first.
    """
    free_at = {p.id: now for p in printers}
    assignable = [p.id for p in printers if p.status not in _UNASSIGNABLE_STATUSES]
    schedule: dict[uuid.UUID, tuple[datetime, datetime, uuid.UUID | None]] = {}

    for job in jobs:
        if job.status != JobStatus.PRINTING:
            continue
        start = _make_aware(job.started_at or job.submitted_at)
        completion = start + timedelta(minutes=_duration_of(job))
        if completion < now:
            completion = now + timedelta(minutes=OVERRUN_GRACE_MIN)
        schedule[job.id] = (start, completion, job.printer_id)
        if job.printer_id in free_at:
            free_at[job.printer_id] = max(free_at[job.printer_id], completion)

    waiting = sorted(
        (j for j in jobs if j.status != JobStatus.PRINTING),
        key=lambda j: _make_aware(j.submitted_at),
    )
    for job in waiting:
        printer_id = job.printer_id
        if printer_id is None and assignable:
            printer_id = min(assignable, key=lambda pid: free_at[pid])
        if printer_id is None or printer_id not in free_at:
            continue
        start = free_at[printer_id]
        completion = start + timedelta(minutes=_duration_of(job))
        free_at[printer_id] = completion
        schedule[job.id] = (start, completion, job.printer_id)

    return schedule


def refresh_queue_estimates(db: Session) -> list[PrintJob]:
    """Recompute and persist estimates for all active jobs; return them oldest first."""
    jobs = list(
        db.scalars(
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
        ).unique()
    )
    printers = list(db.scalars(select(Printer)))
    schedule = compute_queue_schedule(jobs, printers, datetime.now(timezone.utc))
    for job in jobs:
        start, completion, _ = schedule.get(job.id, (None, None, None))
        job.est_start_at = start
        job.est_completion_at = completion
    db.commit()
    return jobs


def get_print_queue(db: Session, user: User | None = None) -> list[QueueTileResponse]:
    """Return the active queue with per-printer estimated start/completion times.

    Estimates are computed over the whole farm so a student's own jobs still
    account for everyone ahead of them; only the output is filtered by role.
    """
    jobs = refresh_queue_estimates(db)
    if user is not None and user.role == UserRole.STUDENT:
        jobs = [j for j in jobs if j.user_id == user.id]

    responses: list[QueueTileResponse] = []
    for job in jobs:
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
                est_start_time=job.est_start_at,
                est_completion_time=job.est_completion_at,
                duration_is_default=not job.est_duration_min,
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

