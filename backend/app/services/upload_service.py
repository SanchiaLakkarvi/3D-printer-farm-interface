"""G-code upload application service.

Narrow safe-upload gate (extension + size) → server-owned storage write →
``run_content_validation_hook`` (slice #3; no-op today) → Print Job in
``pending_selection``. Retention/delete-on-collect is owned by the lifecycle
slice, not this module.
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


def run_content_validation_hook(
    *,
    relative_key: str,
    content: bytes,
    storage_root: str,
) -> None:
    """Slice #3 hook: G-code content validation after the local gate.

    Called once the file exists at ``relative_key`` under ``storage_root`` and
    **before** the Print Job row is committed (validate-then-commit).

    When the validation slice lands, replace this no-op with parse/validate that
    reads the stored path (via ``storage_service`` / ``relative_key``) and/or
    ``content``. On failure raise ``BadRequestError`` (or another ``AppError``);
    the caller deletes the file and leaves no lasting job. On success, optionally
    return metadata for estimates / ``job_validations`` / ``material_id`` without
    renaming status to a dishonest ``validated``.

    See ``Docs/specs/gcode-validation-duration-filament-parse-handoff.md``.
    """
    _ = (relative_key, content, storage_root)
    return


def upload_gcode(
    *,
    db: Session,
    user: User,
    upload: UploadFile,
    storage_root: str | None = None,
) -> PrintJob:
    """Accept a multipart G-code upload and persist a pending_selection job.

    Flow: local gate → write relative key → ``run_content_validation_hook`` (#3)
    → commit job. Validation failure or commit failure cleans up the file and
    leaves no lasting job. Retention/delete-on-collect is owned by the lifecycle
    slice, not this function.
    """
    root = storage_root if storage_root is not None else settings.file_storage_root
    max_bytes = settings.max_upload_bytes

    original_filename = _basename_only(upload.filename)
    extension = _resolve_extension(original_filename)
    content = _read_within_limit(upload, max_bytes)

    job_id = uuid.uuid4()
    relative_key = storage_service.relative_storage_key(user.id, job_id, extension)

    try:
        storage_service.write_bytes(relative_key, content, storage_root=root)
    except Exception:
        # Best-effort cleanup if mkdir/write left partial artifacts; never leak OS paths.
        storage_service.delete_if_exists(relative_key, storage_root=root)
        raise AppError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="UPLOAD_FAILED",
            message="Upload could not be completed",
        ) from None

    try:
        run_content_validation_hook(
            relative_key=relative_key,
            content=content,
            storage_root=root,
        )
    except AppError:
        storage_service.delete_if_exists(relative_key, storage_root=root)
        raise
    except Exception:
        storage_service.delete_if_exists(relative_key, storage_root=root)
        raise AppError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="UPLOAD_FAILED",
            message="Upload could not be completed",
        ) from None

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
