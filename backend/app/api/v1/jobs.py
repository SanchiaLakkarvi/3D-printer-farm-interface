"""Print Queue & History API endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, Response, Header
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_submitter, require_farmer
from app.db.session import get_db
from app.models.user import User
from app.core.config import settings
from app.core.exceptions import PayloadTooLargeError
from app.schemas.job import JobUploadOut
from app.schemas.jobs import (
    GcodeValidationResponse,
    JobSubmissionResponse,
    PrintHistoryResponse,
    QueueTileResponse,
)
from app.services import job_service, submission_service, upload_service, tracking_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/upload", response_model=JobUploadOut, status_code=201)
def upload_gcode(
    file: Annotated[UploadFile, File(description="Pre-sliced .gcode or .gco file")],
    user: Annotated[User, Depends(require_submitter)],
    db: Annotated[Session, Depends(get_db)],
) -> JobUploadOut:
    """Upload a G-code file and create a Print Job in pending_selection.

    Role comes from the authenticated profile (require_submitter hierarchy).
    Client-supplied paths/filenames are never used for on-disk location.
    """
    job = upload_service.upload_gcode(db=db, user=user, upload=file)
    return JobUploadOut(
        id=job.id,
        tracking_url=job.tracking_url,
        submission_id=job.submission_id,
        status=job.status,
        original_filename=job.original_filename or "",
        gcode_path=job.gcode_path,
    )
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


def _read_upload(file: UploadFile) -> bytes:
    """Read an upload, stopping early if it exceeds the size limit."""
    data = file.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise PayloadTooLargeError(
            f"File exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit."
        )
    return data


@router.post("/validate", response_model=GcodeValidationResponse)
def validate_gcode(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(description="Pre-sliced PrusaSlicer .gcode/.bgcode file")],
) -> GcodeValidationResponse:
    """Validate an uploaded G-code file and list compatible printers. Stores nothing."""
    del current_user
    return submission_service.validate_file(
        db=db, filename=file.filename or "", data=_read_upload(file)
    )


@router.post("", response_model=JobSubmissionResponse, status_code=201)
def submit_job(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File(description="Pre-sliced PrusaSlicer .gcode/.bgcode file")],
    printer_id: Annotated[uuid.UUID, Form()],
    material_id: Annotated[uuid.UUID, Form()],
    idempotency_key: Annotated[uuid.UUID | None, Header()] = None,
) -> JobSubmissionResponse:
    """Validate the file for the chosen printer/material and add it to the queue."""
    return submission_service.submit_job(
        db=db,
        user=current_user,
        filename=file.filename or "",
        data=_read_upload(file),
        printer_id=printer_id,
        material_id=material_id,
        submission_id=idempotency_key,
    )


@router.get("/tracking")
def scan_job(
    identifier: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Read a scanned UUID or tracking path with the usual job ownership checks."""
    return tracking_service.tracking(db, tracking_service.lookup(db, current_user, identifier))


@router.get("/{job_id}/qr", response_class=Response)
def job_qr(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    job = tracking_service.lookup(db, current_user, str(job_id))
    if job.qr_svg is None:
        tracking_service.ensure_qr(job)
        db.commit()
    return Response(content=job.qr_svg, media_type="image/svg+xml")


@router.get("/{job_id}")
def track_job(
    job_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    return tracking_service.tracking(db, tracking_service.lookup(db, current_user, str(job_id)))


@router.post("/{job_id}/collect")
def collect_job(
    job_id: uuid.UUID,
    farmer: Annotated[User, Depends(require_farmer)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    job = tracking_service.lookup(db, farmer, str(job_id), lock=True)
    return tracking_service.collect(db, job, farmer)
