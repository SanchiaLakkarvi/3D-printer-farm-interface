"""Tests for G-code upload validation and job submission (uses app.validation)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.auth.fake import FakeAuthAdapter
from app.core.config import settings
from app.models.enums import PrinterStatus, UserRole
from app.models.job_validation import JobValidation
from app.models.material import Material
from app.models.print_job import PrintJob
from app.models.printer import Printer
from app.services.submission_service import parse_duration_min
from tests.test_jobs_reports import STUDENT_EMAIL, STUDENT_PASSWORD, _seed_profile, _token

DATA = Path(__file__).resolve().parents[1] / "app" / "validation" / "data"
SAMPLE = DATA / "Rook1_0.4n_0.15mm_PLA_COREONE_1h5m.gcode"


def _printer(model: str, profile: str, **kwargs) -> Printer:
    return Printer(
        id=uuid.uuid4(),
        model=model,
        status=kwargs.pop("status", PrinterStatus.IDLE),
        bed_size="250x220",
        location="Lab A",
        locked_profile={"validator_profile": profile},
        **kwargs,
    )


@pytest.fixture()
def env(
    auth_client: TestClient,
    db_session: Session,
    auth_adapter: FakeAuthAdapter,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "file_storage_root", str(tmp_path))
    _seed_profile(
        db_session=db_session, auth_adapter=auth_adapter, email=STUDENT_EMAIL,
        password=STUDENT_PASSWORD, role=UserRole.STUDENT,
    )
    pla = Material(id=uuid.uuid4(), name="PLA White", type="PLA", colour="white")
    petg = Material(id=uuid.uuid4(), name="PETG Black", type="PETG", colour="black")
    abs_ = Material(id=uuid.uuid4(), name="ABS Grey", type="ABS", colour="grey")
    core_one = _printer("Prusa CORE One", "core_one_hf04")
    xl = _printer("Prusa XL", "xl_5t_is_04")
    db_session.add_all([pla, petg, abs_, core_one, xl])
    db_session.commit()
    headers = {"Authorization": f"Bearer {_token(auth_client, STUDENT_EMAIL, STUDENT_PASSWORD)}"}
    return dict(client=auth_client, db=db_session, headers=headers, pla=pla, petg=petg,
                abs=abs_, core_one=core_one, xl=xl, tmp=tmp_path)


def _file(path: Path = SAMPLE) -> dict:
    return {"file": (path.name, path.read_bytes(), "text/plain")}


def _submit(env, printer, material, files=None):
    return env["client"].post(
        "/api/jobs",
        headers=env["headers"],
        data={"printer_id": str(printer.id), "material_id": str(material.id)},
        files=files or _file(),
    )


def test_parse_duration() -> None:
    assert parse_duration_min("1h 5m 14s") == pytest.approx(65.23, abs=0.01)
    assert parse_duration_min("1d 2h") == 1560.0
    assert parse_duration_min("garbage") is None
    assert parse_duration_min(None) is None


def test_validate_returns_only_matching_printers(env) -> None:
    resp = env["client"].post("/api/jobs/validate", headers=env["headers"], files=_file())
    assert resp.status_code == 200
    body = resp.json()
    assert body["passed"] is True
    assert body["required_material"] == "PLA"
    assert body["est_duration_min"] == pytest.approx(65.23, abs=0.01)
    assert body["est_filament_g"] == 12.8
    assert body["estimated_cost_usd"] == 2.04
    assert [p["model"] for p in body["compatible_printers"]] == ["Prusa CORE One"]


def test_validate_reports_failure_without_error_status(env) -> None:
    resp = env["client"].post(
        "/api/jobs/validate", headers=env["headers"], files=_file(DATA / "broken_too_hot.gcode")
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["passed"] is False and body["failed_stage"] and body["errors"]
    assert body["compatible_printers"] == []


def test_submit_queues_job_and_stores_file(env) -> None:
    resp = _submit(env, env["core_one"], env["pla"])
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "queued"
    assert body["est_start_time"] and body["est_completion_time"]

    job = env["db"].get(PrintJob, uuid.UUID(body["job_id"]))
    assert Path(job.gcode_path).read_bytes() == SAMPLE.read_bytes()
    assert Path(job.gcode_path).is_relative_to(env["tmp"])
    rows = env["db"].scalars(select(JobValidation).where(JobValidation.job_id == job.id)).all()
    assert len(rows) == 4 and all(r.passed for r in rows)


@pytest.mark.parametrize(
    ("printer_key", "material_key", "code"),
    [
        ("core_one", "petg", "MATERIAL_MISMATCH"),
        ("xl", "pla", "PRINTER_INCOMPATIBLE"),
    ],
)
def test_submit_rejections_store_nothing(env, printer_key, material_key, code) -> None:
    resp = _submit(env, env[printer_key], env[material_key])
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == code
    assert env["db"].scalars(select(PrintJob)).all() == []
    assert not (env["tmp"] / "uploads").exists()


def test_submit_rejects_invalid_gcode(env) -> None:
    resp = _submit(env, env["core_one"], env["pla"], _file(DATA / "broken_too_hot.gcode"))
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "VALIDATION_FAILED"


def test_submit_rejects_unavailable_printer_and_unknown_ids(env) -> None:
    env["core_one"].status = PrinterStatus.OFFLINE
    env["db"].commit()
    assert _submit(env, env["core_one"], env["pla"]).status_code == 409

    ghost = Printer(id=uuid.uuid4(), model="x", bed_size="1x1", location="x")
    assert _submit(env, ghost, env["pla"]).status_code == 404


def test_submit_rejects_empty_and_oversized(env, monkeypatch: pytest.MonkeyPatch) -> None:
    empty = {"file": ("a.gcode", b"", "text/plain")}
    assert _submit(env, env["core_one"], env["pla"], empty).status_code == 400
    monkeypatch.setattr(settings, "max_upload_bytes", 100)
    assert _submit(env, env["core_one"], env["pla"]).status_code == 413


def test_upload_requires_auth(auth_client: TestClient) -> None:
    resp = auth_client.post("/api/jobs/validate", files=_file())
    assert resp.status_code == 401
