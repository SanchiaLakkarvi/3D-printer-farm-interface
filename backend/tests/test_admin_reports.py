"""Unit tests for Admin + Basic Usage Reporting endpoints.

Tests all 5 reporting endpoints:
  GET /api/reports/usage
  GET /api/reports/printers
  GET /api/reports/materials
  GET /api/reports/users
  GET /api/reports/departments

Verifies: KPIs, chart data, date filtering, entity filtering, RBAC.
"""

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

# Test credentials
STUDENT_EMAIL = "student.report@uwa.edu.au"
STUDENT_PASSWORD = "student-password"
FARMER_EMAIL = "farmer.report@uwa.edu.au"
FARMER_PASSWORD = "farmer-password"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_profile(
    *,
    db_session: Session,
    auth_adapter: FakeAuthAdapter,
    email: str,
    password: str,
    role: UserRole,
    first_name: str = "Test",
    last_name: str = "User",
    student_number: str | None = None,
    department: str = "Mechanical Engineering",
) -> User:
    user_id = auth_adapter.seed_user(email=email, password=password)
    user = User(
        id=user_id,
        email=email.lower(),
        first_name=first_name,
        last_name=last_name,
        student_number=student_number,
        role=role,
        department=department,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    return user


def _token(client: TestClient, email: str, password: str) -> str:
    resp = client.post("/api/auth/signin", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _seed_test_data(db_session: Session, student: User) -> dict:
    """Seed 2 printers, 2 materials, and 6 print jobs across 2 departments and 3 dates."""
    now = datetime.now(timezone.utc)

    mat_pla = Material(id=uuid.uuid4(), name="PLA Black", type="PLA", colour="black")
    mat_petg = Material(id=uuid.uuid4(), name="PETG Blue", type="PETG", colour="blue")

    printer_a = Printer(
        id=uuid.uuid4(),
        model="Prusa CORE One",
        status=PrinterStatus.IDLE,
        bed_size="250x210",
        location="Lab A",
        current_material_id=mat_pla.id,
    )
    printer_b = Printer(
        id=uuid.uuid4(),
        model="Prusa XL",
        status=PrinterStatus.PRINTING,
        bed_size="360x360",
        location="Lab B",
        current_material_id=mat_petg.id,
    )
    db_session.add_all([mat_pla, mat_petg, printer_a, printer_b])
    db_session.commit()

    # 6 jobs across different statuses, dates, printers, materials, departments
    jobs = [
        # Job 1: Completed, 90min, Printer A, PLA, Mech Eng, 3 days ago
        PrintJob(
            id=uuid.uuid4(),
            user_id=student.id,
            printer_id=printer_a.id,
            material_id=mat_pla.id,
            gcode_path="/storage/part1.gcode",
            status=JobStatus.COMPLETED,
            est_duration_min=90.0,
            actual_duration_min=90.0,
            est_filament_g=50.0,
            actual_filament_g=48.0,
            department="Mechanical Engineering",
            submitted_at=now - timedelta(days=3),
            completed_at=now - timedelta(days=3, hours=-1),
        ),
        # Job 2: Completed, 120min, Printer B, PETG, Elec Eng, 2 days ago
        PrintJob(
            id=uuid.uuid4(),
            user_id=student.id,
            printer_id=printer_b.id,
            material_id=mat_petg.id,
            gcode_path="/storage/part2.gcode",
            status=JobStatus.COMPLETED,
            est_duration_min=120.0,
            actual_duration_min=120.0,
            est_filament_g=80.0,
            actual_filament_g=75.0,
            department="Electrical Engineering",
            submitted_at=now - timedelta(days=2),
            completed_at=now - timedelta(days=2, hours=-2),
        ),
        # Job 3: Failed, 60min, Printer A, PLA, Mech Eng, 1 day ago
        PrintJob(
            id=uuid.uuid4(),
            user_id=student.id,
            printer_id=printer_a.id,
            material_id=mat_pla.id,
            gcode_path="/storage/part3.gcode",
            status=JobStatus.FAILED,
            est_duration_min=60.0,
            actual_duration_min=30.0,
            est_filament_g=40.0,
            actual_filament_g=20.0,
            department="Mechanical Engineering",
            submitted_at=now - timedelta(days=1),
        ),
        # Job 4: Removed (cancelled), 45min, Printer B, PETG, CS, 1 day ago
        PrintJob(
            id=uuid.uuid4(),
            user_id=student.id,
            printer_id=printer_b.id,
            material_id=mat_petg.id,
            gcode_path="/storage/part4.gcode",
            status=JobStatus.REMOVED,
            est_duration_min=45.0,
            est_filament_g=30.0,
            department="Computer Science",
            submitted_at=now - timedelta(days=1),
        ),
        # Job 5: Queued (active), 30min, Printer A, PLA, Mech Eng, today
        PrintJob(
            id=uuid.uuid4(),
            user_id=student.id,
            printer_id=printer_a.id,
            material_id=mat_pla.id,
            gcode_path="/storage/part5.gcode",
            status=JobStatus.QUEUED,
            est_duration_min=30.0,
            est_filament_g=15.0,
            department="Mechanical Engineering",
            submitted_at=now,
        ),
        # Job 6: Printing (active), 60min, Printer B, PETG, Elec Eng, today
        PrintJob(
            id=uuid.uuid4(),
            user_id=student.id,
            printer_id=printer_b.id,
            material_id=mat_petg.id,
            gcode_path="/storage/part6.gcode",
            status=JobStatus.PRINTING,
            est_duration_min=60.0,
            est_filament_g=35.0,
            department="Electrical Engineering",
            submitted_at=now,
            started_at=now,
        ),
    ]
    db_session.add_all(jobs)
    db_session.commit()

    return {
        "now": now,
        "mat_pla": mat_pla,
        "mat_petg": mat_petg,
        "printer_a": printer_a,
        "printer_b": printer_b,
        "jobs": jobs,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestOverallUsageReport:
    """Tests for GET /api/reports/usage."""

    def test_kpis_and_charts(
        self,
        auth_client: TestClient,
        db_session: Session,
        auth_adapter: FakeAuthAdapter,
    ) -> None:
        student = _seed_profile(
            db_session=db_session, auth_adapter=auth_adapter,
            email=STUDENT_EMAIL, password=STUDENT_PASSWORD, role=UserRole.STUDENT,
            student_number="22709999",
        )
        farmer = _seed_profile(
            db_session=db_session, auth_adapter=auth_adapter,
            email=FARMER_EMAIL, password=FARMER_PASSWORD, role=UserRole.FARMER,
        )
        _seed_test_data(db_session, student)
        token = _token(auth_client, FARMER_EMAIL, FARMER_PASSWORD)

        resp = auth_client.get(
            "/api/reports/usage",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()

        # KPI cards
        assert data["total_jobs"] == 6
        assert data["completed_jobs"] == 2
        assert data["failed_jobs"] == 1
        assert data["cancelled_jobs"] == 1
        assert data["active_queued_jobs"] == 2
        assert data["success_rate_pct"] > 0

        # Chart: jobs_over_time should have entries
        assert len(data["jobs_over_time"]) > 0
        # Chart: status_breakdown should have entries
        assert len(data["status_breakdown"]) > 0

        # Totals should be positive
        assert data["total_print_hours"] > 0
        assert data["total_filament_g"] > 0
        assert data["avg_print_duration_min"] > 0

    def test_date_filter(
        self,
        auth_client: TestClient,
        db_session: Session,
        auth_adapter: FakeAuthAdapter,
    ) -> None:
        student = _seed_profile(
            db_session=db_session, auth_adapter=auth_adapter,
            email=STUDENT_EMAIL, password=STUDENT_PASSWORD, role=UserRole.STUDENT,
            student_number="22709999",
        )
        farmer = _seed_profile(
            db_session=db_session, auth_adapter=auth_adapter,
            email=FARMER_EMAIL, password=FARMER_PASSWORD, role=UserRole.FARMER,
        )
        data = _seed_test_data(db_session, student)
        token = _token(auth_client, FARMER_EMAIL, FARMER_PASSWORD)

        # Filter: only today's jobs (should be 2: queued + printing)
        today = data["now"].strftime("%Y-%m-%dT00:00:00Z")
        resp = auth_client.get(
            f"/api/reports/usage?from_date={today}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        result = resp.json()
        assert result["total_jobs"] == 2
        assert result["active_queued_jobs"] == 2


class TestPrinterReport:
    """Tests for GET /api/reports/printers."""

    def test_per_printer_metrics(
        self,
        auth_client: TestClient,
        db_session: Session,
        auth_adapter: FakeAuthAdapter,
    ) -> None:
        student = _seed_profile(
            db_session=db_session, auth_adapter=auth_adapter,
            email=STUDENT_EMAIL, password=STUDENT_PASSWORD, role=UserRole.STUDENT,
            student_number="22709999",
        )
        farmer = _seed_profile(
            db_session=db_session, auth_adapter=auth_adapter,
            email=FARMER_EMAIL, password=FARMER_PASSWORD, role=UserRole.FARMER,
        )
        _seed_test_data(db_session, student)
        token = _token(auth_client, FARMER_EMAIL, FARMER_PASSWORD)

        resp = auth_client.get(
            "/api/reports/printers",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        printers = resp.json()
        assert len(printers) == 2

        # Each printer should have metrics
        for p in printers:
            assert "printer_id" in p
            assert "model" in p
            assert "total_jobs" in p
            assert "completed_jobs" in p
            assert "failed_jobs" in p
            assert "total_print_hours" in p
            assert "total_filament_g" in p
            assert "utilization_pct" in p
            assert "queue_length" in p

        # Printer A (CORE One): 3 jobs (completed + failed + queued)
        core_one = next(p for p in printers if p["model"] == "Prusa CORE One")
        assert core_one["total_jobs"] == 3
        assert core_one["completed_jobs"] == 1
        assert core_one["failed_jobs"] == 1
        assert core_one["queue_length"] >= 1  # at least the queued job

    def test_failure_rate(
        self,
        auth_client: TestClient,
        db_session: Session,
        auth_adapter: FakeAuthAdapter,
    ) -> None:
        student = _seed_profile(
            db_session=db_session, auth_adapter=auth_adapter,
            email=STUDENT_EMAIL, password=STUDENT_PASSWORD, role=UserRole.STUDENT,
            student_number="22709999",
        )
        farmer = _seed_profile(
            db_session=db_session, auth_adapter=auth_adapter,
            email=FARMER_EMAIL, password=FARMER_PASSWORD, role=UserRole.FARMER,
        )
        _seed_test_data(db_session, student)
        token = _token(auth_client, FARMER_EMAIL, FARMER_PASSWORD)

        resp = auth_client.get(
            "/api/reports/printers",
            headers={"Authorization": f"Bearer {token}"},
        )
        printers = resp.json()

        # Printer A has the failed job
        core_one = next(p for p in printers if p["model"] == "Prusa CORE One")
        assert core_one["failed_jobs"] == 1

        # Printer B has 0 failures
        prusa_xl = next(p for p in printers if p["model"] == "Prusa XL")
        assert prusa_xl["failed_jobs"] == 0


class TestMaterialReport:
    """Tests for GET /api/reports/materials."""

    def test_per_material_and_time_series(
        self,
        auth_client: TestClient,
        db_session: Session,
        auth_adapter: FakeAuthAdapter,
    ) -> None:
        student = _seed_profile(
            db_session=db_session, auth_adapter=auth_adapter,
            email=STUDENT_EMAIL, password=STUDENT_PASSWORD, role=UserRole.STUDENT,
            student_number="22709999",
        )
        farmer = _seed_profile(
            db_session=db_session, auth_adapter=auth_adapter,
            email=FARMER_EMAIL, password=FARMER_PASSWORD, role=UserRole.FARMER,
        )
        _seed_test_data(db_session, student)
        token = _token(auth_client, FARMER_EMAIL, FARMER_PASSWORD)

        resp = auth_client.get(
            "/api/reports/materials",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()

        # 2 materials
        assert len(data["materials"]) == 2

        pla = next(m for m in data["materials"] if m["type"] == "PLA")
        assert pla["material_name"] == "PLA Black"
        assert pla["total_jobs"] == 3  # jobs 1, 3, 5
        assert pla["total_filament_g"] > 0

        petg = next(m for m in data["materials"] if m["type"] == "PETG")
        assert petg["material_name"] == "PETG Blue"
        assert petg["total_jobs"] == 3  # jobs 2, 4, 6

        # Filament over time series should have entries
        assert len(data["filament_over_time"]) > 0


class TestUserReport:
    """Tests for GET /api/reports/users."""

    def test_per_user_activity(
        self,
        auth_client: TestClient,
        db_session: Session,
        auth_adapter: FakeAuthAdapter,
    ) -> None:
        student = _seed_profile(
            db_session=db_session, auth_adapter=auth_adapter,
            email=STUDENT_EMAIL, password=STUDENT_PASSWORD, role=UserRole.STUDENT,
            first_name="Alice", last_name="Smith", student_number="22709999",
        )
        farmer = _seed_profile(
            db_session=db_session, auth_adapter=auth_adapter,
            email=FARMER_EMAIL, password=FARMER_PASSWORD, role=UserRole.FARMER,
        )
        _seed_test_data(db_session, student)
        token = _token(auth_client, FARMER_EMAIL, FARMER_PASSWORD)

        resp = auth_client.get(
            "/api/reports/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        users = resp.json()

        # Only 1 user has jobs
        assert len(users) == 1
        u = users[0]
        assert u["first_name"] == "Alice"
        assert u["last_name"] == "Smith"
        assert u["student_number"] == "22709999"
        assert u["total_jobs"] == 6
        assert u["completed_jobs"] == 2
        assert u["failed_jobs"] == 1
        assert u["total_print_hours"] > 0
        assert u["total_filament_g"] > 0

    def test_department_filter(
        self,
        auth_client: TestClient,
        db_session: Session,
        auth_adapter: FakeAuthAdapter,
    ) -> None:
        student = _seed_profile(
            db_session=db_session, auth_adapter=auth_adapter,
            email=STUDENT_EMAIL, password=STUDENT_PASSWORD, role=UserRole.STUDENT,
            student_number="22709999",
        )
        farmer = _seed_profile(
            db_session=db_session, auth_adapter=auth_adapter,
            email=FARMER_EMAIL, password=FARMER_PASSWORD, role=UserRole.FARMER,
        )
        _seed_test_data(db_session, student)
        token = _token(auth_client, FARMER_EMAIL, FARMER_PASSWORD)

        # Filter by Computer Science department — should find 1 job (the removed one)
        resp = auth_client.get(
            "/api/reports/users?department=Computer+Science",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        users = resp.json()
        assert len(users) == 1
        assert users[0]["total_jobs"] == 1


class TestDepartmentReport:
    """Tests for GET /api/reports/departments."""

    def test_per_department_aggregation(
        self,
        auth_client: TestClient,
        db_session: Session,
        auth_adapter: FakeAuthAdapter,
    ) -> None:
        student = _seed_profile(
            db_session=db_session, auth_adapter=auth_adapter,
            email=STUDENT_EMAIL, password=STUDENT_PASSWORD, role=UserRole.STUDENT,
            student_number="22709999",
        )
        farmer = _seed_profile(
            db_session=db_session, auth_adapter=auth_adapter,
            email=FARMER_EMAIL, password=FARMER_PASSWORD, role=UserRole.FARMER,
        )
        _seed_test_data(db_session, student)
        token = _token(auth_client, FARMER_EMAIL, FARMER_PASSWORD)

        resp = auth_client.get(
            "/api/reports/departments",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        depts = resp.json()

        # 3 departments: Computer Science, Electrical Engineering, Mechanical Engineering
        assert len(depts) == 3

        mech = next(d for d in depts if d["department"] == "Mechanical Engineering")
        assert mech["total_jobs"] == 3  # jobs 1, 3, 5
        assert mech["completed_jobs"] == 1
        assert mech["failed_jobs"] == 1
        assert mech["total_print_hours"] > 0
        assert mech["total_filament_g"] > 0

        elec = next(d for d in depts if d["department"] == "Electrical Engineering")
        assert elec["total_jobs"] == 2  # jobs 2, 6

        cs = next(d for d in depts if d["department"] == "Computer Science")
        assert cs["total_jobs"] == 1  # job 4


class TestRBAC:
    """Tests that students get 403 on all reporting endpoints."""

    REPORT_ENDPOINTS = [
        "/api/reports/usage",
        "/api/reports/printers",
        "/api/reports/materials",
        "/api/reports/users",
        "/api/reports/departments",
    ]

    def test_student_forbidden_all_endpoints(
        self,
        auth_client: TestClient,
        db_session: Session,
        auth_adapter: FakeAuthAdapter,
    ) -> None:
        _seed_profile(
            db_session=db_session, auth_adapter=auth_adapter,
            email=STUDENT_EMAIL, password=STUDENT_PASSWORD, role=UserRole.STUDENT,
            student_number="22709999",
        )
        token = _token(auth_client, STUDENT_EMAIL, STUDENT_PASSWORD)

        for endpoint in self.REPORT_ENDPOINTS:
            resp = auth_client.get(
                endpoint,
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 403, f"Student should get 403 on {endpoint}"


class TestLegacyStatistics:
    """Tests that the deprecated /statistics endpoint still works."""

    def test_deprecated_statistics_still_returns_200(
        self,
        auth_client: TestClient,
        db_session: Session,
        auth_adapter: FakeAuthAdapter,
    ) -> None:
        _seed_profile(
            db_session=db_session, auth_adapter=auth_adapter,
            email=FARMER_EMAIL, password=FARMER_PASSWORD, role=UserRole.FARMER,
        )
        token = _token(auth_client, FARMER_EMAIL, FARMER_PASSWORD)

        resp = auth_client.get(
            "/api/reports/statistics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_jobs" in data
