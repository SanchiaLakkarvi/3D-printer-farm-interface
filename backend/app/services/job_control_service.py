"""Farmer controls for a job that is on a printer: pause and resume.

This only sends the command to the printer. The printer sync loop sees the new
state on its next poll, records ``paused_at`` and notifies the job owner, so
pauses made at the printer itself are handled the same way.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.adapters.printer.factory import build_printer_port
from app.adapters.printer.port import (
    PrinterConflictError,
    PrinterError,
    PrinterPort,
    PrinterUnreachableError,
)
from app.core.exceptions import ConflictError, NotFoundError
from app.models.enums import JobStatus
from app.models.printer import Printer
from app.models.print_job import PrintJob


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
