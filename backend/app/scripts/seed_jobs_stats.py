"""Seed script for populating demo print jobs, queue items, and statistics.
Run with: python backend/app/scripts/seed_jobs_stats.py
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure backend root is on sys.path when executed directly
backend_root = Path(__file__).resolve().parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.db.session import SessionLocal
from app.models.enums import JobStatus, PrinterStatus, UserRole
from app.models.material import Material
from app.models.print_job import PrintJob
from app.models.printer import Printer
from app.models.user import User


def seed_demo_jobs_and_stats() -> None:
    """Populate database with printers, materials, users, and print jobs across states."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        # 1. Materials
        mat_pla = db.query(Material).filter_by(name="PLA Black").first()
        if not mat_pla:
            mat_pla = Material(
                id=uuid.uuid4(), name="PLA Black", type="PLA", colour="black"
            )
            db.add(mat_pla)

        mat_petg = db.query(Material).filter_by(name="PETG White").first()
        if not mat_petg:
            mat_petg = Material(
                id=uuid.uuid4(), name="PETG White", type="PETG", colour="white"
            )
            db.add(mat_petg)

        db.commit()

        # 2. Printers
        p1 = db.query(Printer).filter_by(model="Prusa CORE One").first()
        if not p1:
            p1 = Printer(
                id=uuid.uuid4(),
                model="Prusa CORE One",
                status=PrinterStatus.PRINTING,
                bed_size="250x210",
                location="Lab A - Bay 1",
                current_material_id=mat_pla.id,
            )
            db.add(p1)

        p2 = db.query(Printer).filter_by(model="Prusa XL").first()
        if not p2:
            p2 = Printer(
                id=uuid.uuid4(),
                model="Prusa XL",
                status=PrinterStatus.IDLE,
                bed_size="360x360",
                location="Lab B - Bay 4",
                current_material_id=mat_petg.id,
            )
            db.add(p2)

        db.commit()

        # 3. Users
        student = db.query(User).filter_by(email="student.demo@student.uwa.edu.au").first()
        if not student:
            student = User(
                id=uuid.uuid4(),
                email="student.demo@student.uwa.edu.au",
                first_name="Alice",
                last_name="Student",
                role=UserRole.STUDENT,
                department="Mechanical Engineering",
                created_at=now,
            )
            db.add(student)

        farmer = db.query(User).filter_by(email="farmer.demo@uwa.edu.au").first()
        if not farmer:
            farmer = User(
                id=uuid.uuid4(),
                email="farmer.demo@uwa.edu.au",
                first_name="Bob",
                last_name="Farmer",
                role=UserRole.FARMER,
                department="Mechanical Engineering",
                created_at=now,
            )
            db.add(farmer)

        db.commit()

        # 4. Print Jobs
        # Check if demo jobs already seeded
        existing_jobs = db.query(PrintJob).count()
        if existing_jobs == 0:
            sample_jobs = [
                # Currently printing job
                PrintJob(
                    id=uuid.uuid4(),
                    user_id=student.id,
                    printer_id=p1.id,
                    material_id=mat_pla.id,
                    gcode_path="/storage/prototype_bracket.gcode",
                    status=JobStatus.PRINTING,
                    est_duration_min=45.0,
                    est_filament_g=35.0,
                    department="Mechanical Engineering",
                    submitted_at=now - timedelta(minutes=15),
                ),
                # Queued job
                PrintJob(
                    id=uuid.uuid4(),
                    user_id=student.id,
                    printer_id=p2.id,
                    material_id=mat_petg.id,
                    gcode_path="/storage/gear_housing.gcode",
                    status=JobStatus.QUEUED,
                    est_duration_min=90.0,
                    est_filament_g=80.0,
                    department="Civil Engineering",
                    submitted_at=now - timedelta(minutes=10),
                ),
                # Submitted job
                PrintJob(
                    id=uuid.uuid4(),
                    user_id=student.id,
                    printer_id=None,
                    material_id=mat_pla.id,
                    gcode_path="/storage/sensor_mount.gcode",
                    status=JobStatus.SUBMITTED,
                    est_duration_min=120.0,
                    est_filament_g=110.0,
                    department="Software Engineering",
                    submitted_at=now - timedelta(minutes=5),
                ),
                # Completed job (cost = $2.00 + 0.5 * $0.50 = $2.25 for 90 min)
                PrintJob(
                    id=uuid.uuid4(),
                    user_id=student.id,
                    printer_id=p1.id,
                    material_id=mat_pla.id,
                    gcode_path="/storage/robot_arm_joint.gcode",
                    status=JobStatus.COMPLETED,
                    est_duration_min=90.0,
                    actual_duration_min=90.0,
                    est_filament_g=75.0,
                    actual_filament_g=72.5,
                    department="Mechanical Engineering",
                    submitted_at=now - timedelta(days=1, hours=4),
                    completed_at=now - timedelta(days=1, hours=2, minutes=30),
                ),
                # Completed job (cost = $2.00 for 45 min)
                PrintJob(
                    id=uuid.uuid4(),
                    user_id=student.id,
                    printer_id=p2.id,
                    material_id=mat_petg.id,
                    gcode_path="/storage/drone_propeller.gcode",
                    status=JobStatus.COMPLETED,
                    est_duration_min=45.0,
                    actual_duration_min=45.0,
                    est_filament_g=25.0,
                    actual_filament_g=24.0,
                    department="Civil Engineering",
                    submitted_at=now - timedelta(days=2),
                    completed_at=now - timedelta(days=2) + timedelta(minutes=45),
                ),
                # Failed job
                PrintJob(
                    id=uuid.uuid4(),
                    user_id=student.id,
                    printer_id=p1.id,
                    material_id=mat_pla.id,
                    gcode_path="/storage/test_cube.gcode",
                    status=JobStatus.FAILED,
                    est_duration_min=30.0,
                    actual_duration_min=10.0,
                    est_filament_g=15.0,
                    actual_filament_g=5.0,
                    department="Mechanical Engineering",
                    submitted_at=now - timedelta(days=3),
                    completed_at=now - timedelta(days=3) + timedelta(minutes=10),
                ),
            ]
            db.add_all(sample_jobs)
            db.commit()
            print("Successfully seeded demo print jobs, queue items, and statistics!")
        else:
            print("Demo print jobs already present in database.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_jobs_and_stats()
