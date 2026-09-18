"""HTTP & unit tests for Print Queue, History, Farm Statistics, and Pricing endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.auth.fake import FakeAuthAdapter
from app.models.enums import JobStatus, PrinterStatus, UserRole
from app.models.material import Material
from app.models.print_job import PrintJob
from app.models.printer import Printer
from app.models.user import User
from app.services.pricing_service import calculate_print_cost

STUDENT_EMAIL = "22709999@student.uwa.edu.au"
STUDENT_PASSWORD = "secure-password-jobs"
FARMER_EMAIL = "farmer.jobs@uwa.edu.au"
FARMER_PASSWORD = "farmer-password-jobs"


def _seed_profile(
    *,
    db_session: Session,
    auth_adapter: FakeAuthAdapter,
    email: str,
    password: str,
    role: UserRole,
    department: str = "Mechanical Engineering",
) -> User:
    user_id = auth_adapter.seed_user(email=email, password=password)
    user = User(
        id=user_id,
        email=email.lower(),
        first_name="Test",
        last_name="User",
        student_number="22709999" if role == UserRole.STUDENT else None,
        role=role,
        department=department,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    return user


def _token(auth_client: TestClient, email: str, password: str) -> str:
    response = auth_client.post(
        "/api/auth/signin",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_pricing_formula_calculation() -> None:
    """Verify $2.00 1st hr + $0.50 per additional hour pricing formula."""
    assert calculate_print_cost(None) == 0.0
    assert calculate_print_cost(0) == 0.0
    assert calculate_print_cost(30) == 2.00
    assert calculate_print_cost(60) == 2.00
    assert calculate_print_cost(90) == 2.25
    assert calculate_print_cost(120) == 2.50
    assert calculate_print_cost(180) == 3.00


def test_get_print_queue_timing_estimates(
    auth_client: TestClient, db_session: Session, auth_adapter: FakeAuthAdapter,
) -> None:
    student = _seed_profile(
        db_session=db_session,
        auth_adapter=auth_adapter,
        email=STUDENT_EMAIL,
        password=STUDENT_PASSWORD,
        role=UserRole.STUDENT,
    )
    token = _token(auth_client, STUDENT_EMAIL, STUDENT_PASSWORD)
    now = datetime.now(timezone.utc)

    mat = Material(id=uuid.uuid4(), name="PLA Black", type="PLA", colour="black")
    printer = Printer(
        id=uuid.uuid4(),
        model="Prusa CORE One",
        status=PrinterStatus.PRINTING,
        bed_size="250x210",
        location="Lab A",
        current_material_id=mat.id,
    )
    db_session.add_all([mat, printer])
    db_session.commit()

    job1 = PrintJob(
        id=uuid.uuid4(),
        user_id=student.id,
        printer_id=printer.id,
        material_id=mat.id,
        gcode_path="/storage/test1.gcode",
        status=JobStatus.PRINTING,
        est_duration_min=45.0,
        submitted_at=now - timedelta(minutes=10),
    )
    job2 = PrintJob(
        id=uuid.uuid4(),
        user_id=student.id,
        printer_id=None,
        material_id=mat.id,
        gcode_path="/storage/test2.gcode",
        status=JobStatus.QUEUED,
        est_duration_min=60.0,
        submitted_at=now - timedelta(minutes=5),
    )
    db_session.add_all([job1, job2])
    db_session.commit()

    response = auth_client.get(
        "/api/jobs/queue",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    queue = response.json()
    assert len(queue) == 2
    assert queue[0]["filename"] == "test1.gcode"
    assert queue[0]["status"] == "printing"
    assert queue[0]["assigned_printer"]["model"] == "Prusa CORE One"
    assert queue[0]["est_duration_formatted"] == "45m"
    assert "est_start_time" in queue[0]
    assert "est_completion_time" in queue[0]

    assert queue[1]["filename"] == "test2.gcode"
    assert queue[1]["status"] == "queued"
    assert queue[1]["est_duration_formatted"] == "1h"


def test_get_print_history_statistics_and_pricing(
    auth_client: TestClient, db_session: Session, auth_adapter: FakeAuthAdapter,
) -> None:
    student = _seed_profile(
        db_session=db_session,
        auth_adapter=auth_adapter,
        email=STUDENT_EMAIL,
        password=STUDENT_PASSWORD,
        role=UserRole.STUDENT,
    )
    token = _token(auth_client, STUDENT_EMAIL, STUDENT_PASSWORD)
    now = datetime.now(timezone.utc)

    mat = Material(id=uuid.uuid4(), name="PETG Blue", type="PETG", colour="blue")
    printer = Printer(
        id=uuid.uuid4(),
        model="Prusa XL",
        status=PrinterStatus.IDLE,
        bed_size="360x360",
        location="Lab B",
        current_material_id=mat.id,
    )
    db_session.add_all([mat, printer])
    db_session.commit()

    # Completed job 90 min -> $2.25
    job = PrintJob(
        id=uuid.uuid4(),
        user_id=student.id,
        printer_id=printer.id,
        material_id=mat.id,
        gcode_path="/storage/bracket.gcode",
        status=JobStatus.COMPLETED,
        est_duration_min=90.0,
        actual_duration_min=90.0,
        est_filament_g=50.0,
        actual_filament_g=48.0,
        department="Mechanical Engineering",
        submitted_at=now - timedelta(hours=3),
        completed_at=now - timedelta(hours=1, minutes=30),
    )
    db_session.add(job)
    db_session.commit()

    response = auth_client.get(
        "/api/jobs/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    history = response.json()
    assert len(history) == 1
    assert history[0]["filename"] == "bracket.gcode"
    assert history[0]["status"] == "completed"
    assert history[0]["material_name"] == "PETG Blue"
    assert history[0]["printer_model"] == "Prusa XL"
    assert history[0]["calculated_cost_usd"] == 2.25


def test_get_farm_statistics_reporting(
    auth_client: TestClient, db_session: Session, auth_adapter: FakeAuthAdapter,
) -> None:
    student = _seed_profile(
        db_session=db_session,
        auth_adapter=auth_adapter,
        email=STUDENT_EMAIL,
        password=STUDENT_PASSWORD,
        role=UserRole.STUDENT,
    )
    farmer = _seed_profile(
        db_session=db_session,
        auth_adapter=auth_adapter,
        email=FARMER_EMAIL,
        password=FARMER_PASSWORD,
        role=UserRole.FARMER,
    )
    student_token = _token(auth_client, STUDENT_EMAIL, STUDENT_PASSWORD)
    farmer_token = _token(auth_client, FARMER_EMAIL, FARMER_PASSWORD)
    now = datetime.now(timezone.utc)

    mat = Material(id=uuid.uuid4(), name="PLA Black", type="PLA", colour="black")
    printer = Printer(
        id=uuid.uuid4(),
        model="Prusa CORE One",
        status=PrinterStatus.IDLE,
        bed_size="250x210",
        location="Lab A",
        current_material_id=mat.id,
    )
    db_session.add_all([mat, printer])
    db_session.commit()

    job = PrintJob(
        id=uuid.uuid4(),
        user_id=student.id,
        printer_id=printer.id,
        material_id=mat.id,
        gcode_path="/storage/gear.gcode",
        status=JobStatus.COMPLETED,
        est_duration_min=120.0,
        actual_duration_min=120.0,
        est_filament_g=60.0,
        actual_filament_g=58.0,
        department="Mechanical Engineering",
        submitted_at=now - timedelta(hours=5),
        completed_at=now - timedelta(hours=3),
    )
    db_session.add(job)
    db_session.commit()

    # Student cannot view stats
    std_resp = auth_client.get(
        "/api/reports/statistics",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert std_resp.status_code == 403

    # Farmer can view stats
    farmer_resp = auth_client.get(
        "/api/reports/statistics",
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    assert farmer_resp.status_code == 200
    stats = farmer_resp.json()
    assert stats["total_jobs"] == 1
    assert stats["completed_jobs"] == 1
    assert stats["total_revenue_usd"] == 2.50  # $2.00 + (1.0 * $0.50) = $2.50
    assert len(stats["printer_stats"]) == 1
    assert stats["printer_stats"][0]["model"] == "Prusa CORE One"
    assert len(stats["material_stats"]) == 1
    assert stats["material_stats"][0]["material_name"] == "PLA Black"
    assert len(stats["department_stats"]) == 1
    assert stats["department_stats"][0]["department"] == "Mechanical Engineering"
