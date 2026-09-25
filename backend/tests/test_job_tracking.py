"""QR tracking and durable at-most-once dispatch regression tests."""
import uuid
from datetime import timedelta
from unittest.mock import patch

from sqlalchemy import select

from app.adapters.printer.port import PrinterConflictError, PrinterUnreachableError, PrinterSnapshot, PrinterState
from app.models.enums import JobStatus, UserRole
from app.models.job_event import JobEvent
from app.models.print_job import PrintJob
from app.services import tracking_service
from app.services.printer_sync_service import sync_printer
from tests.test_printer_sync import world, FakePort, NOW
from tests.test_submission import env, _submit


def test_qr_creation_unique_ids_and_lookup(env):
    first = _submit(env, env["core_one"], env["pla"]).json()
    second = _submit(env, env["core_one"], env["pla"]).json()
    assert first["job_id"] != second["job_id"]
    assert first["submission_id"] != second["submission_id"]
    client, headers = env["client"], env["headers"]
    job = env["db"].get(PrintJob, uuid.UUID(first["job_id"]))
    assert job.tracking_url == f"/api/jobs/{job.id}"
    with patch("app.services.tracking_service.qrcode.make", wraps=tracking_service.qrcode.make) as make:
        tracking_service.ensure_qr(job)
        assert make.call_args.args == (job.tracking_url,)
    qr = client.get(f"{job.tracking_url}/qr", headers=headers)
    assert qr.status_code == 200 and "<svg" in qr.text
    assert qr.text == job.qr_svg
    for identifier in (str(job.id), job.tracking_url, f"/jobs/{job.id}"):
        response = client.get("/api/jobs/tracking", params={"identifier": identifier}, headers=headers)
        assert response.status_code == 200
        assert response.json()["job_id"] == str(job.id)
        assert [e["status"] for e in response.json()["events"]] == [
            "CREATED", "VALIDATING", "QUEUED", "ASSIGNED"]
        assert "gcode_path" not in response.json()
    assert client.get(job.tracking_url, headers=headers).status_code == 200
    assert client.get("/api/jobs/tracking", params={"identifier": "https://evil.test/jobs/1"}, headers=headers).status_code == 400
    assert client.get(f"/api/jobs/{uuid.uuid4()}", headers=headers).status_code == 404
    assert client.get(job.tracking_url).status_code == 401



def test_repeated_dispatch_and_status_history(world):
    db, printer, make_job = world
    job = make_job()
    port = FakePort()
    sync_printer(db, printer, port, NOW)
    sync_printer(db, printer, port, NOW)
    assert len(port.uploads) == 1
    assert job.submission_state == "submitted"
    assert [e.status for e in db.scalars(select(JobEvent).order_by(JobEvent.id))] == ["SUBMITTED", "PRINTING"]
    port.snapshot = PrinterSnapshot(state=PrinterState.FINISHED)
    sync_printer(db, printer, port, NOW + timedelta(minutes=30))
    assert job.tracking_status == "COMPLETED"
    # Even an accidental requeue cannot resubmit a successful submission.
    job.status = JobStatus.QUEUED
    db.commit()
    sync_printer(db, printer, port, NOW + timedelta(minutes=31))
    assert len(port.uploads) == 1


def test_lost_response_blocks_retries_and_next_job(world):
    db, printer, make_job = world
    job = make_job()
    make_job(minutes_ago=1)
    port = FakePort()
    calls = []
    def lost_response(*args):
        calls.append(args)
        raise PrinterUnreachableError("Accepted remotely but response lost")
    port.upload_and_start = lost_response
    sync_printer(db, printer, port, NOW)
    db.expire_all()  # simulate a fresh task reading the durable state
    sync_printer(db, printer, port, NOW)
    assert len(calls) == 1
    assert job.submission_state == "unknown"
    assert job.tracking_status == "SUBMISSION_UNKNOWN"


def test_committed_claim_blocks_reentrant_worker(world):
    db, printer, make_job = world
    job = make_job()
    make_job(minutes_ago=1)
    port = FakePort()
    original = port.upload_and_start
    def overlapping(*args):
        assert job.submission_state == "sending"
        sync_printer(db, printer, FakePort(), NOW)
        original(*args)
    port.upload_and_start = overlapping
    sync_printer(db, printer, port, NOW)
    assert len(port.uploads) == 1


def test_definitive_conflict_can_retry(world):
    db, printer, make_job = world
    job = make_job()
    port = FakePort()
    port.raise_on_upload = PrinterConflictError("refused")
    sync_printer(db, printer, port, NOW)
    assert job.submission_state == "pending"
    port.raise_on_upload = None
    sync_printer(db, printer, port, NOW)
    sync_printer(db, printer, port, NOW)
    assert len(port.uploads) == 1


def test_collection_permissions_and_idempotency(env):
    body = _submit(env, env["core_one"], env["pla"]).json()
    db, client, headers = env["db"], env["client"], env["headers"]
    job = db.get(PrintJob, uuid.UUID(body["job_id"]))
    url = f"/api/jobs/{job.id}/collect"
    assert client.post(url, headers=headers).status_code == 403
    job.user.role = UserRole.FARMER
    db.commit()
    assert client.post(url, headers=headers).status_code == 409
    job.status = JobStatus.COMPLETED
    tracking_service.record(db, job, "COMPLETED")
    db.commit()
    first = client.post(url, headers=headers)
    assert first.status_code == 200
    assert first.json()["status"] == "COLLECTED"
    assert [e["status"] for e in first.json()["events"]][-3:] == ["COMPLETED", "READY_FOR_COLLECTION", "COLLECTED"]
    assert client.post(url, headers=headers).json() == first.json()
    db.refresh(job)
    assert job.collection_record.collected_at is not None
    assert job.status == JobStatus.COMPLETED  # operational history/report semantics preserved


def test_http_submission_retry_reuses_job(env):
    from tests.test_submission import _file
    key = str(uuid.uuid4())
    headers = {**env["headers"], "Idempotency-Key": key}
    data = {"printer_id": str(env["core_one"].id), "material_id": str(env["pla"].id)}
    first = env["client"].post("/api/jobs", headers=headers, data=data, files=_file())
    second = env["client"].post("/api/jobs", headers=headers, data=data, files=_file())
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert len(env["db"].scalars(select(PrintJob)).all()) == 1
    data["material_id"] = str(env["petg"].id)
    assert env["client"].post("/api/jobs", headers=headers, data=data, files=_file()).status_code == 409


def test_crash_after_remote_acceptance_does_not_resubmit(world):
    import pytest
    db, printer, make_job = world
    job = make_job()
    port = FakePort()
    original = port.upload_and_start
    def crash(*args):
        original(*args)
        raise RuntimeError("worker terminated after remote acceptance")
    port.upload_and_start = crash
    with pytest.raises(RuntimeError):
        sync_printer(db, printer, port, NOW)
    db.rollback()
    port.snapshot = PrinterSnapshot(state=PrinterState.READY)
    sync_printer(db, printer, port, NOW)
    assert job.submission_state == "sending"
    assert len(port.uploads) == 1


def test_scan_hides_other_students_jobs(env):
    from tests.test_jobs_reports import _seed_profile
    from app.adapters.auth.fake import FakeAuthAdapter
    first = _submit(env, env["core_one"], env["pla"]).json()
    other = _seed_profile(db_session=env["db"], auth_adapter=FakeAuthAdapter(),
                          email="other@uwa.edu.au", password="password-123", role=UserRole.STUDENT)
    job = env["db"].get(PrintJob, uuid.UUID(first["job_id"]))
    job.user_id = other.id
    env["db"].commit()
    for url in (job.tracking_url, f"{job.tracking_url}/qr"):
        assert env["client"].get(url, headers=env["headers"]).status_code == 404
