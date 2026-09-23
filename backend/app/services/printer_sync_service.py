"""Keep jobs and printers in step with what the printers report.

``sync_printer`` reads a printer's state through its PrinterPort, moves the
active job to printing/completed/failed accordingly, and sends the next queued
job when the printer is free. It is safe to call repeatedly.
"""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.printer.factory import build_printer_port
from app.adapters.printer.port import (
    PrinterConflictError,
    PrinterError,
    PrinterPort,
    PrinterSnapshot,
    PrinterState,
    PrinterUnreachableError,
)
from app.db.session import SessionLocal
from app.models.enums import JobStatus, NotificationType, PrinterStatus
from app.models.notification import Notification
from app.models.print_job import PrintJob
from app.models.printer import Printer

log = logging.getLogger(__name__)

# A printer keeps reporting FINISHED/STOPPED until cleared, so right after a job
# starts those readings may belong to the previous job. Faults are not delayed.
START_GRACE = timedelta(seconds=15)

_ACTIVE = {PrinterState.PRINTING, PrinterState.PAUSED}
_FAULT = {PrinterState.ERROR, PrinterState.ATTENTION}
_READY_FOR_JOB = {PrinterState.IDLE, PrinterState.READY, PrinterState.FINISHED, PrinterState.STOPPED}


def _notify(db: Session, job: PrintJob, kind: NotificationType, message: str, now: datetime) -> None:
    db.add(
        Notification(
            id=uuid.uuid4(),
            user_id=job.user_id,
            job_id=job.id,
            type=kind,
            message=message,
            is_read=False,
            sent_at=now,
        )
    )


def _discard_file(job: PrintJob) -> None:
    """Print files are not kept after a successful print (client requirement)."""
    try:
        os.remove(job.gcode_path)
        os.rmdir(os.path.dirname(job.gcode_path))
    except OSError:
        pass


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _active_job(db: Session, printer: Printer) -> PrintJob | None:
    return db.scalars(
        select(PrintJob).where(
            PrintJob.printer_id == printer.id, PrintJob.status == JobStatus.PRINTING
        )
    ).first()


def _finish(db: Session, job: PrintJob, ok: bool, reason: str, now: datetime) -> None:
    job.status = JobStatus.COMPLETED if ok else JobStatus.FAILED
    job.completed_at = now
    if ok:
        job.actual_filament_g = job.est_filament_g
        _notify(db, job, NotificationType.JOB_COMPLETED, "Your print has finished.", now)
        _discard_file(job)
    else:
        _notify(db, job, NotificationType.JOB_ERROR, f"Your print failed: {reason}", now)


def _apply_active_job(db: Session, job: PrintJob, snap: PrinterSnapshot, now: datetime) -> None:
    """Update the printing job from a snapshot."""
    if snap.job_id is not None:
        job.printer_job_id = snap.job_id
    if snap.time_printing_s is not None:
        job.actual_duration_min = round(snap.time_printing_s / 60.0, 2)

    if snap.state in _ACTIVE:
        return
    if snap.state in _FAULT:
        # A printer in a fault state is never sent a new job, so this is genuine.
        _finish(db, job, False, f"printer reported {snap.state.value}", now)
        return
    if now - _aware(job.started_at or now) < START_GRACE:
        return  # FINISHED/STOPPED/idle may still be the previous job's reading
    if snap.state is PrinterState.FINISHED:
        _finish(db, job, True, "", now)
    elif snap.state is PrinterState.STOPPED:
        _finish(db, job, False, "printer reported STOPPED", now)
    elif snap.state in {PrinterState.IDLE, PrinterState.READY}:
        _finish(db, job, False, "printer no longer reports the job", now)


def _dispatch_next(db: Session, printer: Printer, port: PrinterPort, now: datetime) -> None:
    job = db.scalars(
        select(PrintJob)
        .where(
            PrintJob.printer_id == printer.id,
            PrintJob.status.in_([JobStatus.SUBMITTED, JobStatus.QUEUED]),
        )
        .order_by(PrintJob.submitted_at.asc())
    ).first()
    if job is None:
        return
    try:
        port.upload_and_start(f"{job.id}.gcode", Path(job.gcode_path))
    except PrinterConflictError:
        return
    except (PrinterError, OSError) as exc:
        log.warning("Could not start job %s on printer %s: %s", job.id, printer.id, exc)
        return

    job.status = JobStatus.PRINTING
    job.started_at = now
    printer.status = PrinterStatus.PRINTING
    _notify(db, job, NotificationType.JOB_STARTED, "Your print has started.", now)
    db.commit()
    try:
        job.printer_job_id = port.get_status().job_id
        db.commit()
    except PrinterError:
        pass


def sync_printer(db: Session, printer: Printer, port: PrinterPort, now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    if printer.status is PrinterStatus.MAINTENANCE:
        return  # admin has taken it out of service

    try:
        snap = port.get_status()
    except PrinterUnreachableError:
        printer.status = PrinterStatus.OFFLINE
        db.commit()
        return
    except PrinterError as exc:
        log.warning("Printer %s returned an error: %s", printer.id, exc)
        printer.status = PrinterStatus.ERROR
        db.commit()
        return

    job = _active_job(db, printer)
    if job is not None:
        _apply_active_job(db, job, snap, now)

    if snap.state in _ACTIVE:
        printer.status = PrinterStatus.PRINTING
    elif snap.state in {PrinterState.ERROR, PrinterState.ATTENTION}:
        printer.status = PrinterStatus.ERROR
    elif snap.state is not PrinterState.BUSY:
        printer.status = PrinterStatus.IDLE
    db.commit()

    if snap.state in _READY_FOR_JOB and _active_job(db, printer) is None:
        _dispatch_next(db, printer, port, now)


def sync_all_printers(
    session_factory: Callable[[], Session] = SessionLocal,
    port_factory: Callable[[Printer], PrinterPort | None] = build_printer_port,
) -> None:
    """Sync every printer that has a PrusaLink connection."""
    db = session_factory()
    try:
        for printer in db.scalars(select(Printer)).all():
            port = port_factory(printer)
            if port is None:
                continue
            try:
                sync_printer(db, printer, port)
            except Exception:
                db.rollback()
                log.exception("Sync failed for printer %s", printer.id)
            finally:
                port.close()
    finally:
        db.close()
