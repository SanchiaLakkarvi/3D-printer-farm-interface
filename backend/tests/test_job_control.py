"""HTTP tests for farmer pause/resume of a printing job."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.auth.fake import FakeAuthAdapter
from app.adapters.printer.port import PrinterConflictError, PrinterUnreachableError
from app.models.collection_record import CollectionRecord
from app.models.enums import JobStatus, NotificationType, PrinterStatus, UserRole
from app.models.material import Material
from app.models.notification import Notification
from app.models.print_job import PrintJob
from app.models.printer import Printer
from app.services import job_control_service
from tests.test_jobs_reports import (
    FARMER_EMAIL,
    FARMER_PASSWORD,
    STUDENT_EMAIL,
    STUDENT_PASSWORD,
    _seed_profile,
    _token,
)

NOW = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)


class RecordingPort:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []
        self.raise_on_control: Exception | None = None
        self.closed = False

    def _control(self, action: str, job_id: int) -> None:
        if self.raise_on_control:
            raise self.raise_on_control
        self.calls.append((action, job_id))

    def pause_job(self, job_id: int) -> None:
        self._control("pause", job_id)

    def resume_job(self, job_id: int) -> None:
        self._control("resume", job_id)

    def close(self) -> None:
        self.closed = True


@pytest.fixture()
def farm(auth_client: TestClient, db_session: Session, auth_adapter: FakeAuthAdapter, monkeypatch, tmp_path: Path):
    student = _seed_profile(
        db_session=db_session, auth_adapter=auth_adapter, email=STUDENT_EMAIL,
        password=STUDENT_PASSWORD, role=UserRole.STUDENT,
    )
    _seed_profile(
        db_session=db_session, auth_adapter=auth_adapter, email=FARMER_EMAIL,
        password=FARMER_PASSWORD, role=UserRole.FARMER,
    )
    material = Material(id=uuid.uuid4(), name="PLA", type="PLA", colour="white")
    printer = Printer(
        id=uuid.uuid4(), model="Prusa CORE One", status=PrinterStatus.PRINTING,
        bed_size="250x220", location="Lab", prusalink_url="http://p.test",
    )
    db_session.add_all([material, printer])
    db_session.commit()

    def make_job(status: JobStatus = JobStatus.PRINTING, printer_job_id: int | None = 7) -> PrintJob:
        job_id = uuid.uuid4()
        folder = tmp_path / str(job_id)
        folder.mkdir()
        gcode = folder / "part.gcode"
        gcode.write_text("G28\n")
        job = PrintJob(
            id=job_id, user_id=student.id, printer_id=printer.id, material_id=material.id,
            gcode_path=str(gcode), original_filename="part.gcode", status=status, est_duration_min=60.0,
            submitted_at=NOW - timedelta(minutes=10), started_at=NOW - timedelta(minutes=5),
            printer_job_id=printer_job_id,
        )
        db_session.add(job)
        db_session.commit()
        return job

    port = RecordingPort()
    monkeypatch.setattr(job_control_service, "build_printer_port", lambda _printer: port)

    def headers(email: str, password: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {_token(auth_client, email, password)}"}

    return make_job, port, headers(FARMER_EMAIL, FARMER_PASSWORD), headers(STUDENT_EMAIL, STUDENT_PASSWORD)


@pytest.mark.parametrize("action", ["pause", "resume"])
def test_farmer_sends_command_to_printer(auth_client: TestClient, farm, action: str) -> None:
    make_job, port, farmer, _ = farm
    job = make_job()

    response = auth_client.post(f"/api/jobs/{job.id}/{action}", headers=farmer)

    assert response.status_code == 202
    assert response.json() == {"job_id": str(job.id), "action": action}
    assert port.calls == [(action, 7)] and port.closed


def test_student_cannot_pause(auth_client: TestClient, farm) -> None:
    make_job, port, _, student = farm
    job = make_job()
    assert auth_client.post(f"/api/jobs/{job.id}/pause", headers=student).status_code == 403
    assert port.calls == []


def test_requires_sign_in(auth_client: TestClient) -> None:
    assert auth_client.post(f"/api/jobs/{uuid.uuid4()}/pause").status_code == 401


def test_unknown_job_is_404(auth_client: TestClient, farm) -> None:
    _, _, farmer, _ = farm
    assert auth_client.post(f"/api/jobs/{uuid.uuid4()}/pause", headers=farmer).status_code == 404


@pytest.mark.parametrize(
    ("status", "printer_job_id"),
    [(JobStatus.QUEUED, None), (JobStatus.COMPLETED, 7), (JobStatus.PRINTING, None)],
)
def test_only_a_printing_job_on_a_printer_can_be_paused(
    auth_client: TestClient, farm, status: JobStatus, printer_job_id: int | None,
) -> None:
    make_job, port, farmer, _ = farm
    job = make_job(status, printer_job_id)

    response = auth_client.post(f"/api/jobs/{job.id}/pause", headers=farmer)

    assert response.status_code == 409
    assert port.calls == []


@pytest.mark.parametrize(
    ("error", "code"),
    [(PrinterConflictError("not paused"), 409), (PrinterUnreachableError("down"), 503)],
)
def test_printer_errors_are_reported(auth_client: TestClient, farm, error: Exception, code: int) -> None:
    make_job, port, farmer, _ = farm
    job = make_job()
    port.raise_on_control = error

    response = auth_client.post(f"/api/jobs/{job.id}/resume", headers=farmer)

    assert response.status_code == code
    assert port.closed


def test_farmer_collects_completed_print_and_notifies_student(
    auth_client: TestClient, db_session: Session, farm,
) -> None:
    make_job, _, farmer, _ = farm
    job = make_job(JobStatus.COMPLETED)
    path = Path(job.gcode_path)

    response = auth_client.post(f"/api/jobs/{job.id}/collect", headers=farmer)

    assert response.status_code == 200
    assert response.json() == {"job_id": str(job.id), "action": "collect"}
    db_session.refresh(job)
    assert job.status is JobStatus.READY_FOR_COLLECTION
    record = db_session.scalars(select(CollectionRecord).where(CollectionRecord.job_id == job.id)).one()
    assert record.farmer_id is not None
    assert record.removed_at is not None and record.ready_at is not None
    notification = db_session.scalars(
        select(Notification).where(Notification.job_id == job.id)
    ).one()
    assert notification.user_id == job.user_id
    assert notification.type is NotificationType.READY_FOR_COLLECTION
    assert notification.message == "Your print part.gcode is ready to collect."
    assert not path.exists()


def test_collect_is_idempotent(auth_client: TestClient, db_session: Session, farm) -> None:
    make_job, _, farmer, _ = farm
    job = make_job(JobStatus.COMPLETED)

    first = auth_client.post(f"/api/jobs/{job.id}/collect", headers=farmer)
    second = auth_client.post(f"/api/jobs/{job.id}/collect", headers=farmer)

    assert first.status_code == second.status_code == 200
    assert len(db_session.scalars(select(CollectionRecord).where(CollectionRecord.job_id == job.id)).all()) == 1
    assert len(db_session.scalars(select(Notification).where(Notification.job_id == job.id)).all()) == 1


def test_student_cannot_collect_completed_print(auth_client: TestClient, farm) -> None:
    make_job, _, _, student = farm
    job = make_job(JobStatus.COMPLETED)
    assert auth_client.post(f"/api/jobs/{job.id}/collect", headers=student).status_code == 403


def test_only_completed_print_can_be_collected(auth_client: TestClient, farm) -> None:
    make_job, _, farmer, _ = farm
    job = make_job(JobStatus.FAILED)
    response = auth_client.post(f"/api/jobs/{job.id}/collect", headers=farmer)
    assert response.status_code == 409
