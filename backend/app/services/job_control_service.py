"""Farmer controls for pausing, resuming, and collecting prints.

Pause and resume send commands to the printer; the sync loop records their
state changes. Collection confirms physical removal, records the farmer action,
and notifies the job owner.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.printer.factory import build_printer_port
from app.adapters.printer.port import (
    PrinterConflictError,
    PrinterError,
    PrinterPort,
    PrinterUnreachableError,
)
from app.core.exceptions import ConflictError, NotFoundError
from app.models.collection_record import CollectionRecord
from app.models.enums import JobStatus, NotificationType
from app.models.notification import Notification
from app.models.printer import Printer
from app.models.print_job import PrintJob
from app.models.user import User


def _send(
    db: Session,
    job_id: uuid.UUID,
    action: str,
    port_factory: Callable[[Printer], PrinterPort | None] | None,
) -> PrintJob:
    job = db.get(PrintJob, job_id)
    if job is None:
        raise NotFoundError("Print job", str(job_id))
    if job.status is not JobStatus.PRINTING or job.printer is None or job.printer_job_id is None:
        raise ConflictError(f"Only a job that is printing can be {action}d.")
    port = (port_factory or build_printer_port)(job.printer)
    if port is None:
        raise ConflictError("This printer has no PrusaLink connection.")
    try:
        getattr(port, f"{action}_job")(job.printer_job_id)
    except PrinterConflictError as exc:
        raise ConflictError(f"The printer refused to {action} the job in its current state.") from exc
    except PrinterUnreachableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "PRINTER_UNREACHABLE", "message": "Cannot reach the printer."},
        ) from exc
    except PrinterError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "PRINTER_ERROR", "message": f"The printer could not {action} the job."},
        ) from exc
    finally:
        port.close()
    return job


def pause_job(
    db: Session,
    job_id: uuid.UUID,
    port_factory: Callable[[Printer], PrinterPort | None] | None = None,
) -> PrintJob:
    return _send(db, job_id, "pause", port_factory)


def resume_job(
    db: Session,
    job_id: uuid.UUID,
    port_factory: Callable[[Printer], PrinterPort | None] | None = None,
) -> PrintJob:
    return _send(db, job_id, "resume", port_factory)


def mark_ready_for_collection(
    db: Session,
    job_id: uuid.UUID,
    farmer: User,
    now: datetime | None = None,
) -> PrintJob:
    """Record physical removal and notify the owner that the print can be collected."""
    job = db.scalars(
        select(PrintJob).where(PrintJob.id == job_id).with_for_update()
    ).first()
    if job is None:
        raise NotFoundError("Print job", str(job_id))
    if job.status is JobStatus.READY_FOR_COLLECTION:
        return job
    if job.status is not JobStatus.COMPLETED:
        raise ConflictError("Only a completed print can be marked ready for collection.")

    ready_at = now or datetime.now(timezone.utc)
    job.status = JobStatus.READY_FOR_COLLECTION
    db.add(
        CollectionRecord(
            id=uuid.uuid4(),
            job_id=job.id,
            farmer_id=farmer.id,
            removed_at=ready_at,
            ready_at=ready_at,
        )
    )
    name = job.original_filename or os.path.basename(job.gcode_path) or "Your print"
    db.add(
        Notification(
            id=uuid.uuid4(),
            user_id=job.user_id,
            job_id=job.id,
            type=NotificationType.READY_FOR_COLLECTION,
            message=f"Your print {name} is ready to collect.",
            is_read=False,
            sent_at=ready_at,
        )
    )
    db.commit()

    # The successful file is no longer needed after the physical print is removed.
    try:
        os.remove(job.gcode_path)
        os.rmdir(os.path.dirname(job.gcode_path))
    except OSError:
        pass
    return job
