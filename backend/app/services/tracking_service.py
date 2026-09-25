"""Safe QR payloads, tracking history and collection using existing job records."""
import io
import uuid
from datetime import datetime, timezone

import qrcode
import qrcode.image.svg
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.collection_record import CollectionRecord
from app.models.enums import JobStatus, UserRole
from app.models.job_event import JobEvent
from app.models.print_job import PrintJob
from app.models.user import User


def record(db: Session, job: PrintJob, status: str) -> None:
    if job.tracking_status != status:
        job.tracking_status = status
        db.add(JobEvent(job_id=job.id, status=status))


def ensure_qr(job: PrintJob) -> None:
    job.tracking_url = f"/api/jobs/{job.id}"
    output = io.BytesIO()
    qrcode.make(job.tracking_url, image_factory=qrcode.image.svg.SvgPathImage).save(output)
    job.qr_svg = output.getvalue().decode("utf-8")


def initialize(db: Session, job: PrintJob) -> None:
    ensure_qr(job)
    record(db, job, "CREATED")


def lookup(db: Session, user: User, identifier: str, *, lock: bool = False) -> PrintJob:
    value = identifier.removeprefix("/api/jobs/").removeprefix("/jobs/")
    try:
        job_id = uuid.UUID(value)
    except ValueError:
        raise BadRequestError("INVALID_TRACKING_ID", "Use a job UUID or job tracking path.") from None
    query = select(PrintJob).where(PrintJob.id == job_id)
    if user.role == UserRole.STUDENT:
        query = query.where(PrintJob.user_id == user.id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    job = db.scalar(query)
    if job is None:
        raise NotFoundError("Job", str(job_id))
    return job


def tracking(db: Session, job: PrintJob) -> dict:
    events = db.scalars(select(JobEvent).where(JobEvent.job_id == job.id).order_by(JobEvent.id)).all()
    return {
        "job_id": job.id, "tracking_url": job.tracking_url,
        "status": job.tracking_status or job.status.value.upper(),
        "queue_status": job.status, "printer_id": job.printer_id,
        "submission_id": job.submission_id, "submission_state": job.submission_state,
        "events": [{"status": e.status, "occurred_at": e.occurred_at} for e in events],
    }


def collect(db: Session, job: PrintJob, user: User) -> dict:
    if job.tracking_status == "COLLECTED":
        return tracking(db, job)
    if job.status not in {JobStatus.COMPLETED, JobStatus.READY_FOR_COLLECTION}:
        raise ConflictError("Only completed jobs can be collected.")
    now = datetime.now(timezone.utc)
    collection = job.collection_record
    if collection is None:
        collection = CollectionRecord(id=uuid.uuid4(), job_id=job.id, farmer_id=user.id)
        db.add(collection)
    if collection.ready_at is None:
        collection.ready_at = now
        record(db, job, "READY_FOR_COLLECTION")
    collection.collected_at = now
    record(db, job, "COLLECTED")
    db.commit()
    return tracking(db, job)
