"""Metadata contract tests for SQLAlchemy models vs agreed live schema.

These tests inspect Base.metadata only — no database connection.
Models reflect Alembic head (after 0004): auth-profile shape with Role
``student``, ``first_name``/``last_name``, nullable ``student_number``, no
``auth_hash``; ``department`` (not ``unit_code``); no ``queue_position``;
Phase B indexes present.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect as sa_inspect

from app.db.base import Base
from app.models import (  # noqa: F401 — register metadata
    CheckType,
    CollectionRecord,
    JobStatus,
    JobValidation,
    MaintenanceLog,
    Material,
    Notification,
    NotificationType,
    PrintJob,
    Printer,
    PrinterStatus,
    User,
    UserRole,
)

EXPECTED_TABLES = {
    "users",
    "materials",
    "printers",
    "print_jobs",
    "job_validations",
    "notifications",
    "collection_records",
    "maintenance_logs",
}

VERSIONS_DIR = Path(__file__).resolve().parents[1] / "alembic" / "versions"


def _table(name: str):
    assert name in Base.metadata.tables
    return Base.metadata.tables[name]


def _index_names(table_name: str) -> set[str]:
    table = _table(table_name)
    return {index.name for index in table.indexes if index.name is not None}


def _unique_constraint_names(table_name: str) -> set[str]:
    table = _table(table_name)
    return {
        c.name
        for c in table.constraints
        if c.name and c.__class__.__name__ == "UniqueConstraint"
    }


def test_all_expected_tables_registered() -> None:
    assert EXPECTED_TABLES <= set(Base.metadata.tables)


def test_users_email_unique_and_department_nullable() -> None:
    users = _table("users")
    assert "users_email_key" in _unique_constraint_names("users")
    assert users.c.department.nullable is True
    assert users.c.email.nullable is False
    assert "auth_hash" not in users.c


def test_users_auth_profile_shape() -> None:
    """Agreed Supabase Auth profile: split names, nullable student_number."""
    users = _table("users")
    assert "name" not in users.c
    assert "student_staff_number" not in users.c
    assert users.c.first_name.nullable is False
    assert users.c.last_name.nullable is False
    assert users.c.student_number.nullable is True


def test_print_jobs_nullability_and_no_queue_position() -> None:
    jobs = _table("print_jobs")
    assert jobs.c.printer_id.nullable is True
    assert jobs.c.department.nullable is True
    assert jobs.c.material_id.nullable is False
    assert "queue_position" not in jobs.c


def test_notifications_job_id_nullable() -> None:
    assert _table("notifications").c.job_id.nullable is True


def test_collection_records_job_id_unique() -> None:
    assert "collection_records_job_id_key" in _unique_constraint_names(
        "collection_records"
    )


def test_printer_locked_profile_and_validation_message_nullable() -> None:
    assert _table("printers").c.locked_profile.nullable is True
    assert _table("job_validations").c.message.nullable is True


def test_collection_timestamp_columns_nullable() -> None:
    records = _table("collection_records")
    assert records.c.ready_at.nullable is True
    assert records.c.removed_at.nullable is True
    assert records.c.collected_at.nullable is True
    assert records.c.notes.nullable is True


def test_enum_names_and_values() -> None:
    assert {m.value for m in UserRole} == {"student", "farmer", "admin"}
    assert {m.value for m in PrinterStatus} == {
        "idle",
        "printing",
        "error",
        "offline",
        "maintenance",
    }
    assert {m.value for m in JobStatus} == {
        "submitted",
        "queued",
        "printing",
        "completed",
        "failed",
        "removed",
        "ready_for_collection",
    }
    assert {m.value for m in CheckType} == {
        "printer_compatibility",
        "material_compatibility",
        "bed_size",
        "config",
    }
    assert {m.value for m in NotificationType} == {
        "job_started",
        "job_completed",
        "job_error",
        "ready_for_collection",
    }

    assert _table("users").c.role.type.name == "user_role"
    assert _table("printers").c.status.type.name == "printer_status"
    assert _table("print_jobs").c.status.type.name == "job_status"
    assert _table("job_validations").c.check_type.type.name == "check_type"
    assert _table("notifications").c.type.type.name == "notification_type"


def test_baseline_indexes_present_in_metadata() -> None:
    assert {
        "idx_print_jobs_user_id",
        "idx_print_jobs_printer_id",
        "idx_print_jobs_status",
    } <= _index_names("print_jobs")
    assert "idx_job_validations_job_id" in _index_names("job_validations")
    assert {
        "idx_notifications_user_id",
        "idx_notifications_user_is_read",
    } <= _index_names("notifications")
    assert "idx_collection_records_job_id" in _index_names("collection_records")
    assert "idx_maintenance_logs_printer_id" in _index_names("maintenance_logs")


def test_phase_b_indexes_present_in_metadata() -> None:
    assert "idx_printers_current_material_id" in _index_names("printers")
    assert "idx_print_jobs_material_id" in _index_names("print_jobs")
    assert "idx_print_jobs_queue_submitted_at" in _index_names("print_jobs")
    assert "idx_notifications_job_id" in _index_names("notifications")
    assert "idx_collection_records_farmer_id" in _index_names("collection_records")
    assert "idx_maintenance_logs_farmer_id" in _index_names("maintenance_logs")


def test_explicit_fk_constraint_names() -> None:
    jobs = _table("print_jobs")
    fk_names = {fk.name for fk in jobs.foreign_keys}
    assert {
        "print_jobs_user_id_fkey",
        "print_jobs_printer_id_fkey",
        "print_jobs_material_id_fkey",
    } <= fk_names


def test_mapper_configuration_loads() -> None:
    """Ensure relationships resolve without circular-import errors."""
    sa_inspect(User)
    sa_inspect(PrintJob)
    sa_inspect(Printer)
    sa_inspect(CollectionRecord)


def test_baseline_revision_still_creates_queue_position() -> None:
    baseline = (VERSIONS_DIR / "0001_baseline_existing_schema.py").read_text()
    followup = (VERSIONS_DIR / "0002_queue_indexes_drop_queue_position.py").read_text()
    rename = (VERSIONS_DIR / "0003_rename_unit_code_to_department.py").read_text()
    auth_profile = (
        VERSIONS_DIR / "0004_users_auth_profile_supabase_model.py"
    ).read_text()
    assert 'sa.Column("queue_position", sa.Integer(), nullable=True)' in baseline
    assert 'sa.Column("department", sa.Text(), nullable=True)' in baseline
    assert 'op.drop_column("print_jobs", "queue_position")' in followup
    assert 'revision: str = "0001_baseline_existing_schema"' in baseline
    assert 'revision: str = "0002_queue_indexes_drop_queue_position"' in followup
    assert 'revision: str = "0003_rename_unit_code_to_department"' in rename
    assert 'revision: str = "0004_users_auth_profile_supabase_model"' in auth_profile
    assert 'down_revision' in followup and "0001_baseline_existing_schema" in followup
    assert "0002_queue_indexes_drop_queue_position" in rename
    assert "0003_rename_unit_code_to_department" in auth_profile
    assert "RENAME VALUE" in auth_profile or "student_staff" in auth_profile
    assert "first_name" in auth_profile and "student_number" in auth_profile
    assert "auth_hash" in auth_profile
