"""Tests for printer sync: dispatching queued jobs and tracking printer state."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.auth.fake import FakeAuthAdapter
from app.adapters.printer.port import (
    PrinterConflictError,
    PrinterError,
    PrinterSnapshot,
    PrinterState,
    PrinterUnreachableError,
)
from app.models.enums import JobStatus, NotificationType, PrinterStatus, UserRole
from app.models.material import Material
from app.models.notification import Notification
from app.models.print_job import PrintJob
from app.models.printer import Printer
from app.services.printer_sync_service import START_GRACE, sync_all_printers, sync_printer
from tests.test_jobs_reports import STUDENT_EMAIL, STUDENT_PASSWORD, _seed_profile

NOW = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)


class FakePort:
    def __init__(self, state: PrinterState = PrinterState.READY, **snap) -> None:
        self.snapshot = PrinterSnapshot(state=state, **snap)
        self.uploads: list[tuple[str, Path]] = []
        self.raise_on_status: Exception | None = None
        self.raise_on_upload: Exception | None = None
        self.closed = False

    def get_status(self) -> PrinterSnapshot:
        if self.raise_on_status:
            raise self.raise_on_status
        return self.snapshot

    def upload_and_start(self, remote_name: str, local_path: Path) -> None:
        if self.raise_on_upload:
            raise self.raise_on_upload
        self.uploads.append((remote_name, local_path))
        self.snapshot = PrinterSnapshot(state=PrinterState.PRINTING, job_id=7)

    def stop_job(self, job_id: int) -> None: ...

    def pause_job(self, job_id: int) -> None: ...

    def resume_job(self, job_id: int) -> None: ...

    def close(self) -> None:
        self.closed = True


@pytest.fixture()
def world(db_session: Session, auth_adapter: FakeAuthAdapter, tmp_path: Path):
    user = _seed_profile(
        db_session=db_session, auth_adapter=auth_adapter, email=STUDENT_EMAIL,
        password=STUDENT_PASSWORD, role=UserRole.STUDENT,
    )
    material = Material(id=uuid.uuid4(), name="PLA", type="PLA", colour="white")
    printer = Printer(
        id=uuid.uuid4(), model="Prusa CORE One", status=PrinterStatus.IDLE,
        bed_size="250x220", location="Lab", prusalink_url="http://p.test",
    )
    db_session.add_all([material, printer])
    db_session.commit()

    def make_job(status=JobStatus.QUEUED, minutes_ago=5, **kwargs) -> PrintJob:
        job_id = uuid.uuid4()
        folder = tmp_path / str(job_id)
        folder.mkdir()
        path = folder / "part.gcode"
        path.write_text("G28\n")
        job = PrintJob(
            id=job_id, user_id=user.id, printer_id=printer.id, material_id=material.id,
            gcode_path=str(path), status=status, est_duration_min=60.0, est_filament_g=10.0,
            submitted_at=NOW - timedelta(minutes=minutes_ago), **kwargs,
        )
        db_session.add(job)
        db_session.commit()
        return job

    return db_session, printer, make_job


def _utc(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; treat them as UTC."""
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _notifications(db: Session) -> list[NotificationType]:
    return [n.type for n in db.scalars(select(Notification).order_by(Notification.sent_at))]


def _messages(db: Session) -> list[str]:
    return [n.message for n in db.scalars(select(Notification).order_by(Notification.sent_at))]


def test_dispatches_oldest_queued_job_to_free_printer(world) -> None:
    db, printer, make_job = world
    older = make_job(minutes_ago=10)
    newer = make_job(minutes_ago=2)
    port = FakePort()

    sync_printer(db, printer, port, NOW)

    assert port.uploads == [(f"{older.id}.gcode", Path(older.gcode_path))]
    assert (older.status, newer.status) == (JobStatus.PRINTING, JobStatus.QUEUED)
    assert _utc(older.started_at) == NOW and older.printer_job_id == 7
    assert printer.status is PrinterStatus.PRINTING
    assert _notifications(db) == [NotificationType.JOB_STARTED]


def test_does_not_dispatch_while_printing_or_when_busy(world) -> None:
    db, printer, make_job = world
    make_job()
    printing = FakePort(PrinterState.PRINTING)
    sync_printer(db, printer, printing, NOW)
    assert printing.uploads == []

    conflict = FakePort()
    conflict.raise_on_upload = PrinterConflictError("busy")
    sync_printer(db, printer, conflict, NOW)
    assert db.scalars(select(PrintJob)).one().status is JobStatus.QUEUED


def test_progress_is_recorded_while_printing(world) -> None:
    db, printer, make_job = world
    job = make_job(JobStatus.PRINTING, started_at=NOW - timedelta(minutes=1))
    port = FakePort(PrinterState.PRINTING, job_id=3, progress_pct=40.0, time_printing_s=1800)

    sync_printer(db, printer, port, NOW)

    assert job.status is JobStatus.PRINTING
    assert job.printer_job_id == 3 and job.actual_duration_min == 30.0


def test_finished_completes_job_and_starts_next(world) -> None:
    db, printer, make_job = world
    done = make_job(JobStatus.PRINTING, started_at=NOW - timedelta(minutes=30))
    nxt = make_job(minutes_ago=1)
    folder = Path(done.gcode_path).parent
    port = FakePort(PrinterState.FINISHED)

    sync_printer(db, printer, port, NOW)

    assert done.status is JobStatus.COMPLETED and _utc(done.completed_at) == NOW
    assert done.actual_filament_g == 10.0
    assert not folder.exists()  # print file is not kept after completion
    assert nxt.status is JobStatus.PRINTING
    assert _notifications(db) == [NotificationType.JOB_COMPLETED, NotificationType.JOB_STARTED]


def test_stale_finished_reading_does_not_end_a_new_job(world) -> None:
    db, printer, make_job = world
    job = make_job(JobStatus.PRINTING, started_at=NOW - START_GRACE + timedelta(seconds=1))
    sync_printer(db, printer, FakePort(PrinterState.FINISHED), NOW)
    assert job.status is JobStatus.PRINTING


@pytest.mark.parametrize("state", [PrinterState.ERROR, PrinterState.ATTENTION, PrinterState.STOPPED])
def test_error_states_fail_the_job_and_keep_the_file(world, state: PrinterState) -> None:
    db, printer, make_job = world
    job = make_job(JobStatus.PRINTING, started_at=NOW - timedelta(minutes=5))

    sync_printer(db, printer, FakePort(state), NOW)

    assert job.status is JobStatus.FAILED and _utc(job.completed_at) == NOW
    assert Path(job.gcode_path).exists()  # kept so the job can be reprinted
    assert NotificationType.JOB_ERROR in _notifications(db)
    expected = PrinterStatus.IDLE if state is PrinterState.STOPPED else PrinterStatus.ERROR
    assert printer.status is expected


@pytest.mark.parametrize("state", [PrinterState.ERROR, PrinterState.ATTENTION])
def test_faults_fail_the_job_immediately_even_right_after_start(world, state: PrinterState) -> None:
    db, printer, make_job = world
    job = make_job(JobStatus.PRINTING, started_at=NOW - timedelta(seconds=3))
    sync_printer(db, printer, FakePort(state), NOW)
    assert job.status is JobStatus.FAILED
    assert printer.status is PrinterStatus.ERROR


def test_idle_printer_that_lost_the_job_fails_it(world) -> None:
    db, printer, make_job = world
    job = make_job(JobStatus.PRINTING, started_at=NOW - timedelta(minutes=5))
    sync_printer(db, printer, FakePort(PrinterState.IDLE), NOW)
    assert job.status is JobStatus.FAILED


def test_messages_name_the_file_and_printer(world) -> None:
    db, printer, make_job = world
    job = make_job()
    sync_printer(db, printer, FakePort(), NOW)
    sync_printer(db, printer, FakePort(PrinterState.FINISHED), NOW + timedelta(minutes=5))

    assert _messages(db) == [
        "part.gcode on Prusa CORE One (Lab) has started printing.",
        "part.gcode on Prusa CORE One (Lab) has finished printing.",
    ]
    assert job.status is JobStatus.COMPLETED


def test_original_filename_is_preferred_in_messages(world) -> None:
    db, printer, make_job = world
    make_job(original_filename="rook.gcode")
    sync_printer(db, printer, FakePort(), NOW)
    assert _messages(db) == ["rook.gcode on Prusa CORE One (Lab) has started printing."]


@pytest.mark.parametrize(
    ("state", "reason"),
    [
        (PrinterState.ERROR, "the printer reported an error"),
        (PrinterState.ATTENTION, "the printer needs attention"),
        (PrinterState.STOPPED, "the print was stopped at the printer"),
        (PrinterState.IDLE, "the printer is no longer running it"),
    ],
)
def test_failure_messages_explain_why(world, state: PrinterState, reason: str) -> None:
    db, printer, make_job = world
    make_job(JobStatus.PRINTING, started_at=NOW - timedelta(minutes=5))
    sync_printer(db, printer, FakePort(state), NOW)
    assert _messages(db)[0] == f"part.gcode on Prusa CORE One (Lab) failed: {reason}."


def test_pause_and_resume_notify_the_owner_once_each(world) -> None:
    db, printer, make_job = world
    job = make_job(JobStatus.PRINTING, started_at=NOW - timedelta(minutes=5))

    sync_printer(db, printer, FakePort(PrinterState.PAUSED), NOW)
    sync_printer(db, printer, FakePort(PrinterState.PAUSED), NOW + timedelta(seconds=2))
    assert _utc(job.paused_at) == NOW and job.status is JobStatus.PRINTING
    assert printer.status is PrinterStatus.PRINTING

    sync_printer(db, printer, FakePort(PrinterState.PRINTING), NOW + timedelta(seconds=4))
    sync_printer(db, printer, FakePort(PrinterState.PRINTING), NOW + timedelta(seconds=6))
    assert job.paused_at is None

    assert _notifications(db) == [NotificationType.JOB_PAUSED, NotificationType.JOB_RESUMED]
    assert _messages(db) == [
        "part.gcode on Prusa CORE One (Lab) has been paused.",
        "part.gcode on Prusa CORE One (Lab) has resumed printing.",
    ]


def test_job_that_ends_while_paused_clears_paused_at(world) -> None:
    db, printer, make_job = world
    job = make_job(JobStatus.PRINTING, started_at=NOW - timedelta(minutes=5))
    sync_printer(db, printer, FakePort(PrinterState.PAUSED), NOW)
    sync_printer(db, printer, FakePort(PrinterState.STOPPED), NOW + timedelta(seconds=2))

    assert job.status is JobStatus.FAILED and job.paused_at is None
    assert _notifications(db) == [NotificationType.JOB_PAUSED, NotificationType.JOB_ERROR]


def test_unreachable_printer_goes_offline_and_jobs_are_untouched(world) -> None:
    db, printer, make_job = world
    job = make_job(JobStatus.PRINTING, started_at=NOW - timedelta(minutes=5))
    port = FakePort()
    port.raise_on_status = PrinterUnreachableError("down")

    sync_printer(db, printer, port, NOW)

    assert printer.status is PrinterStatus.OFFLINE and job.status is JobStatus.PRINTING


def test_printer_error_response_marks_printer_error(world) -> None:
    db, printer, make_job = world
    port = FakePort()
    port.raise_on_status = PrinterError("HTTP 500")
    sync_printer(db, printer, port, NOW)
    assert printer.status is PrinterStatus.ERROR


def test_maintenance_printer_is_left_alone(world) -> None:
    db, printer, make_job = world
    printer.status = PrinterStatus.MAINTENANCE
    db.commit()
    make_job()
    port = FakePort()
    sync_printer(db, printer, port, NOW)
    assert port.uploads == [] and printer.status is PrinterStatus.MAINTENANCE


def test_recovered_printer_returns_to_idle(world) -> None:
    db, printer, _ = world
    printer.status = PrinterStatus.OFFLINE
    db.commit()
    sync_printer(db, printer, FakePort(PrinterState.READY), NOW)
    assert printer.status is PrinterStatus.IDLE


def test_sync_all_skips_unconfigured_printers_and_closes_ports(world) -> None:
    db, printer, make_job = world
    make_job()
    bare = Printer(id=uuid.uuid4(), model="Prusa XL", bed_size="360x360", location="Lab",
                   status=PrinterStatus.IDLE)
    db.add(bare)
    db.commit()
    printer_id = printer.id  # sync_all closes the session it is given
    ports: dict[uuid.UUID, FakePort] = {}

    def factory(p: Printer):
        if not p.prusalink_url:
            return None
        return ports.setdefault(p.id, FakePort())

    sync_all_printers(session_factory=lambda: db, port_factory=factory)

    assert list(ports) == [printer_id]
    assert ports[printer_id].closed and len(ports[printer_id].uploads) == 1
