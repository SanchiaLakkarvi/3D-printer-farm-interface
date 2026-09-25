"""Upload validation and job submission.

G-code is validated by ``app.validation.gcode_validator``. This service maps
its result onto database printers and materials, stores accepted files and
queues the job.
"""

from __future__ import annotations

import os
import hashlib
import re
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PayloadTooLargeError,
    UnprocessableError,
)
from app.models.enums import CheckType, JobStatus, PrinterStatus
from app.models.job_validation import JobValidation
from app.models.material import Material
from app.models.print_job import PrintJob
from app.models.printer import Printer
from app.models.user import User
from app.schemas.jobs import (
    CompatiblePrinter,
    GcodeValidationResponse,
    JobSubmissionResponse,
    ValidationStageOut,
)
from app.services.job_service import refresh_queue_estimates
from app.services import tracking_service
from app.services.pricing_service import calculate_print_cost
from app.validation.gcode_validator import validate_upload as run_validator

# Only these are offered: ABS/ASA can emit harmful fumes (client meeting, 11 Sep).
APPROVED_MATERIALS = frozenset({"PLA", "PETG"})

_UNAVAILABLE = frozenset({PrinterStatus.ERROR, PrinterStatus.OFFLINE, PrinterStatus.MAINTENANCE})
_DURATION_PART = re.compile(r"(\d+)\s*([dhms])")
_SECONDS = {"d": 86400, "h": 3600, "m": 60, "s": 1}


def parse_duration_min(text: str | None) -> float | None:
    """Parse PrusaSlicer durations like ``1d 2h 5m 14s`` into minutes."""
    parts = _DURATION_PART.findall(text or "")
    if not parts:
        return None
    return round(sum(int(n) * _SECONDS[u] for n, u in parts) / 60.0, 2)


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_filename(filename: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(filename)).lstrip(".")
    return name or "print_job.gcode"


def _profile_of(printer: Printer) -> str | None:
    profile = (printer.locked_profile or {}).get("validator_profile")
    return profile if isinstance(profile, str) else None


def _run_validator(filename: str, data: bytes) -> dict[str, Any]:
    if not data:
        raise BadRequestError("EMPTY_FILE", "Uploaded file is empty.")
    if len(data) > settings.max_upload_bytes:
        raise PayloadTooLargeError(
            f"File exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit."
        )
    with tempfile.TemporaryDirectory(prefix="gcode-upload-") as tmp:
        path = os.path.join(tmp, _safe_filename(filename))
        with open(path, "wb") as fh:
            fh.write(data)
        return run_validator(path)


def _stages(result: dict[str, Any]) -> list[ValidationStageOut]:
    return [
        ValidationStageOut(stage=s["stage"], name=s["name"], status=s["status"])
        for s in result.get("validation_stages", [])
    ]


def validate_file(db: Session, filename: str, data: bytes) -> GcodeValidationResponse:
    """Validate an upload and list the printers it can run on. Stores nothing."""
    result = _run_validator(filename, data)
    duration = parse_duration_min(result.get("estimated_print_time"))
    response = GcodeValidationResponse(
        filename=_safe_filename(filename),
        passed=bool(result["passed"]),
        message=result["message"],
        errors=result.get("errors", []),
        failed_stage=result.get("failed_stage"),
        stages=_stages(result),
    )
    if not result["passed"]:
        return response

    profile = result["compatible_profile"]
    printers = db.scalars(select(Printer).order_by(Printer.model))
    response.required_material = result.get("required_material")
    response.est_duration_min = duration
    response.est_filament_g = _to_float(result.get("filament_used_g"))
    response.estimated_cost_usd = calculate_print_cost(duration)
    response.compatible_printers = [
        CompatiblePrinter(
            printer_id=p.id, model=p.model, location=p.location, status=p.status
        )
        for p in printers
        if _profile_of(p) == profile
    ]
    return response


def submit_job(
    db: Session,
    user: User,
    filename: str,
    data: bytes,
    printer_id: uuid.UUID,
    material_id: uuid.UUID,
    submission_id: uuid.UUID | None = None,
) -> JobSubmissionResponse:
    """Validate, store and queue a job for the chosen printer and material."""
    fingerprint = hashlib.sha256(
        str(printer_id).encode() + str(material_id).encode() + filename.encode() + hashlib.sha256(data).digest()
    ).hexdigest()
    if submission_id is not None:
        # Serialize repeated HTTP requests by owner without changing queue ordering.
        db.execute(select(User.id).where(User.id == user.id).with_for_update()).one()
        existing = db.scalar(select(PrintJob).where(PrintJob.submission_id == submission_id))
        if existing is not None:
            if existing.user_id != user.id or existing.request_fingerprint != fingerprint:
                raise ConflictError("Idempotency-Key was already used for another submission.")
            return _submission_response(existing)
    printer = db.get(Printer, printer_id)
    if printer is None:
        raise NotFoundError("Printer", str(printer_id))
    material = db.get(Material, material_id)
    if material is None:
        raise NotFoundError("Material", str(material_id))
    if printer.status in _UNAVAILABLE:
        raise ConflictError(f"Printer is {printer.status.value} and cannot accept jobs.")

    result = _run_validator(filename, data)
    if not result["passed"]:
        raise UnprocessableError(
            "VALIDATION_FAILED",
            result["message"],
            {"errors": result.get("errors", []), "failed_stage": result.get("failed_stage")},
        )
    if _profile_of(printer) != result["compatible_profile"]:
        raise UnprocessableError(
            "PRINTER_INCOMPATIBLE",
            f"This file is sliced for {result['compatible_printer']}, "
            f"which does not match printer {printer.model}.",
        )
    required = (result.get("required_material") or "").upper()
    if required not in APPROVED_MATERIALS:
        raise UnprocessableError(
            "MATERIAL_NOT_APPROVED",
            f"{required or 'This material'} is not approved; use one of: "
            f"{', '.join(sorted(APPROVED_MATERIALS))}.",
        )
    if material.type.upper() != required:
        raise UnprocessableError(
            "MATERIAL_MISMATCH",
            f"G-code is sliced for {required} but {material.type} was selected.",
        )

    duration = parse_duration_min(result.get("estimated_print_time"))
    if not duration:
        raise UnprocessableError("NO_DURATION", "G-code has no estimated printing time.")

    job_id = uuid.uuid4()
    safe_name = _safe_filename(filename)
    job_dir = os.path.join(settings.file_storage_root, "uploads", str(job_id))
    os.makedirs(job_dir, exist_ok=True)
    path = os.path.join(job_dir, safe_name)
    with open(path, "wb") as fh:
        fh.write(data)

    now = datetime.now(timezone.utc)
    job = PrintJob(
        id=job_id,
        submission_id=submission_id or uuid.uuid4(),
        request_fingerprint=fingerprint,
        original_filename=safe_name,
        user_id=user.id,
        printer_id=printer.id,
        material_id=material.id,
        gcode_path=path,
        status=JobStatus.QUEUED,
        est_duration_min=duration,
        est_filament_g=_to_float(result.get("filament_used_g")),
        department=user.department,
        submitted_at=now,
    )
    db.add(job)
    passed_checks = {
        CheckType.CONFIG: "File format, integrity, metadata and printer commands are valid.",
        CheckType.PRINTER_COMPATIBILITY: f"Matches {result['compatible_printer']}.",
        CheckType.BED_SIZE: "Print fits the printer build volume.",
        CheckType.MATERIAL_COMPATIBILITY: f"{required} is approved and matches the selection.",
    }
    db.add_all(
        JobValidation(
            id=uuid.uuid4(), job_id=job_id, check_type=kind, passed=True,
            message=message, checked_at=now,
        )
        for kind, message in passed_checks.items()
    )
    try:
        db.flush()
        tracking_service.initialize(db, job)
        for status in ("VALIDATING", "QUEUED", "ASSIGNED"):
            tracking_service.record(db, job, status)
        db.commit()
    except Exception:
        db.rollback()
        os.remove(path)
        os.rmdir(job_dir)
        raise

    refresh_queue_estimates(db)
    db.refresh(job)
    return _submission_response(job)


def _submission_response(job: PrintJob) -> JobSubmissionResponse:
    return JobSubmissionResponse(
        job_id=job.id,
        tracking_url=job.tracking_url,
        submission_id=job.submission_id,
        filename=job.original_filename or os.path.basename(job.gcode_path),
        status=job.status,
        printer_id=job.printer_id,
        est_duration_min=job.est_duration_min,
        est_filament_g=job.est_filament_g,
        estimated_cost_usd=calculate_print_cost(job.est_duration_min),
        est_start_time=job.est_start_at,
        est_completion_time=job.est_completion_at,
    )
