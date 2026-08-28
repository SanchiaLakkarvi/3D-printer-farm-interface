"""Postgres enum types matching the live Supabase schema."""

from __future__ import annotations

import enum

from sqlalchemy import Enum as SAEnum


class UserRole(str, enum.Enum):
    STUDENT_STAFF = "student_staff"
    FARMER = "farmer"
    ADMIN = "admin"


class PrinterStatus(str, enum.Enum):
    IDLE = "idle"
    PRINTING = "printing"
    ERROR = "error"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class JobStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    QUEUED = "queued"
    PRINTING = "printing"
    COMPLETED = "completed"
    FAILED = "failed"
    REMOVED = "removed"
    READY_FOR_COLLECTION = "ready_for_collection"


class CheckType(str, enum.Enum):
    PRINTER_COMPATIBILITY = "printer_compatibility"
    MATERIAL_COMPATIBILITY = "material_compatibility"
    BED_SIZE = "bed_size"
    CONFIG = "config"


class NotificationType(str, enum.Enum):
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_ERROR = "job_error"
    READY_FOR_COLLECTION = "ready_for_collection"


def _pg_enum(enum_cls: type[enum.Enum], name: str) -> SAEnum:
    """Native Postgres ENUM with labels matching live values."""
    return SAEnum(
        enum_cls,
        name=name,
        values_callable=lambda members: [m.value for m in members],
        create_type=True,
        native_enum=True,
    )


user_role_enum = _pg_enum(UserRole, "user_role")
printer_status_enum = _pg_enum(PrinterStatus, "printer_status")
job_status_enum = _pg_enum(JobStatus, "job_status")
check_type_enum = _pg_enum(CheckType, "check_type")
notification_type_enum = _pg_enum(NotificationType, "notification_type")
