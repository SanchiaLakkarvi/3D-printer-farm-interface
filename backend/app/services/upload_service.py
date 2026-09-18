"""G-code upload application service.

Narrow safe-upload gate (extension + size) → server-owned storage write →
Print Job in ``pending_selection``. Full G-code validation is owned by a
later slice; this module leaves a clear hook for it.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError, BadRequestError
from app.models.enums import JobStatus
from app.models.print_job import PrintJob
from app.models.user import User
from app.services import storage_service


def _basename_only(filename: str | None) -> str:
    if not filename:
        return ""
    return Path(filename).name


def _resolve_extension(original_basename: str) -> str:
    suffix = Path(original_basename).suffix.lower()
    if suffix not in storage_service.ALLOWED_EXTENSIONS:
        raise BadRequestError(
            code="INVALID_EXTENSION",
            message="Only .gcode and .gco files are accepted",
        )
    return suffix


def _read_within_limit(upload: UploadFile, max_bytes: int) -> bytes:
    """Read the upload, rejecting when it exceeds the configured maximum."""
    upload.file.seek(0)
    chunk_size = 64 * 1024
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = upload.file.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise BadRequestError(
                code="FILE_TOO_LARGE",
                message=f"File exceeds maximum upload size of {max_bytes} bytes",
            )
        chunks.append(chunk)
    if total == 0:
        raise BadRequestError(
            code="EMPTY_FILE",
            message="Uploaded file is empty",
        )
    return b"".join(chunks)


def upload_gcode(
    *,
    db: Session,
    user: User,
    upload: UploadFile,
    storage_root: str | None = None,
) -> PrintJob:
    """Accept a multipart G-code upload and persist a pending_selection job.

    Validation beyond the local gate (content/profile/material) is deferred.
    When the validation slice lands, call it after the gate and before commit
    (validate-then-commit); on failure, delete the file and do not leave a job.
    """
    root = storage_root if storage_root is not None else settings.file_storage_root
    max_bytes = settings.max_upload_bytes

    original_filename = _basename_only(upload.filename)
    extension = _resolve_extension(original_filename)
    content = _read_within_limit(upload, max_bytes)

    job_id = uuid.uuid4()
    relative_key = storage_service.relative_storage_key(user.id, job_id, extension)

    storage_service.write_bytes(relative_key, content, storage_root=root)

    job = PrintJob(
        id=job_id,
        user_id=user.id,
        printer_id=None,
        material_id=None,
        gcode_path=relative_key,
        original_filename=original_filename,
        status=JobStatus.PENDING_SELECTION,
        est_duration_min=None,
        est_filament_g=None,
        department=user.department,
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(job)
    try:
        db.commit()
        db.refresh(job)
    except Exception:
        db.rollback()
        storage_service.delete_if_exists(relative_key, storage_root=root)
        raise AppError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="UPLOAD_FAILED",
            message="Upload could not be completed",
        ) from None

    return job
