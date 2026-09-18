"""Tests for per-printer queue timing estimates."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.auth.fake import FakeAuthAdapter
from app.models.enums import JobStatus, PrinterStatus, UserRole
from app.models.material import Material
from app.models.print_job import PrintJob
from app.models.printer import Printer
from app.services.job_service import compute_queue_schedule
from tests.test_jobs_reports import (
    STUDENT_EMAIL,
    STUDENT_PASSWORD,
    _seed_profile,
    _token,
)


def _printer(model: str = "Prusa CORE One", **kwargs) -> Printer:
    defaults = dict(
        id=uuid.uuid4(),
        model=model,
        status=PrinterStatus.IDLE,
        bed_size="250x220",
        location="Lab A",
        locked_profile={"printer_model": "COREONE", "nozzle_diameter": 0.4},
    )
    defaults.update(kwargs)
    return Printer(**defaults)


def _job(user_id, material_id, status, minutes, submitted, **kwargs) -> PrintJob:
    return PrintJob(
        id=uuid.uuid4(),
        user_id=user_id,
        material_id=material_id,
        gcode_path="/storage/x.gcode",
        status=status,
        est_duration_min=minutes,
        submitted_at=submitted,
        **kwargs,
    )


# --- queue timing -----------------------------------------------------------


def test_queue_is_scheduled_per_printer() -> None:
    now = datetime.now(timezone.utc)
    user, mat = uuid.uuid4(), uuid.uuid4()
    a, b = _printer(), _printer("Prusa XL")
    printing_a = _job(user, mat, JobStatus.PRINTING, 60, now - timedelta(minutes=50), printer_id=a.id,
                      started_at=now - timedelta(minutes=20))
    queued_a = _job(user, mat, JobStatus.QUEUED, 30, now - timedelta(minutes=10), printer_id=a.id)
    queued_b = _job(user, mat, JobStatus.QUEUED, 30, now - timedelta(minutes=9), printer_id=b.id)
    unassigned = _job(user, mat, JobStatus.QUEUED, 15, now - timedelta(minutes=8))

    sched = compute_queue_schedule([printing_a, queued_a, queued_b, unassigned], [a, b], now)

    # Printing job runs from its real start, not from submission.
    assert sched[printing_a.id][0] == now - timedelta(minutes=20)
    assert sched[printing_a.id][1] == now + timedelta(minutes=40)
    # A's queue follows A's printing job; B's queue starts immediately (not behind A).
    assert sched[queued_a.id][0] == now + timedelta(minutes=40)
    assert sched[queued_b.id][0] == now
    # Unassigned job takes B, which frees up first (at +30) versus A (at +70).
    assert sched[unassigned.id][0] == now + timedelta(minutes=30)


def test_queue_overrun_and_unavailable_printers() -> None:
    now = datetime.now(timezone.utc)
    user, mat = uuid.uuid4(), uuid.uuid4()
    a = _printer()
    down = _printer("Prusa XL", status=PrinterStatus.OFFLINE)
    overrun = _job(user, mat, JobStatus.PRINTING, 30, now - timedelta(hours=2), printer_id=a.id,
                   started_at=now - timedelta(hours=1))
    waiting = _job(user, mat, JobStatus.QUEUED, 10, now)
    sched = compute_queue_schedule([overrun, waiting], [a, down], now)
    assert sched[overrun.id][1] == now + timedelta(minutes=5)
    assert sched[waiting.id][0] == now + timedelta(minutes=5)  # never the offline printer

    assert compute_queue_schedule([waiting], [down], now) == {}


def test_student_queue_estimates_include_other_users_jobs(
    auth_client: TestClient, db_session: Session, auth_adapter: FakeAuthAdapter
) -> None:
    student = _seed_profile(
        db_session=db_session, auth_adapter=auth_adapter, email=STUDENT_EMAIL,
        password=STUDENT_PASSWORD, role=UserRole.STUDENT,
    )
    other = _seed_profile(
        db_session=db_session, auth_adapter=auth_adapter, email="other@student.uwa.edu.au",
        password="another-password-1", role=UserRole.STUDENT,
    )
    mat = Material(id=uuid.uuid4(), name="PLA", type="PLA", colour="white")
    printer = _printer()
    now = datetime.now(timezone.utc)
    db_session.add_all([mat, printer])
    db_session.commit()
    db_session.add_all([
        _job(other.id, mat.id, JobStatus.QUEUED, 120, now - timedelta(minutes=5), printer_id=printer.id),
        _job(student.id, mat.id, JobStatus.QUEUED, 30, now, printer_id=printer.id),
    ])
    db_session.commit()

    token = _token(auth_client, STUDENT_EMAIL, STUDENT_PASSWORD)
    queue = auth_client.get("/api/jobs/queue", headers={"Authorization": f"Bearer {token}"}).json()
    assert len(queue) == 1  # other user's job is hidden...
    start = datetime.fromisoformat(queue[0]["est_start_time"])
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    # ...but the student still waits behind it.
    assert start - now >= timedelta(minutes=119)
