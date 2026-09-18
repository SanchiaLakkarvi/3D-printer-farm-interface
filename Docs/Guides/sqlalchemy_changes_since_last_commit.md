# SQLAlchemy Schema Implementation — Changes Since Last Commit

**Baseline commit:** `55de3bd` — *Merge pull request #27 from SanchiaLakkarvi/feature/fastapi-backend-setup*  
**Document date:** 26 August 2026  
**Status:** Uncommitted working-tree changes (not yet in git history)

> **Update (26 Aug 2026 evening):** `unit_code` was renamed to `department` on
> `users` and `print_jobs` (Supabase live + Alembic `0003` + SQLAlchemy models).
> Use department values such as `engineering`, `IT`, `mechanical` for admin
> cost/usage reporting. Embedded file dumps below may still show the older
> `unit_code` name — trust the live source files under `backend/app/models/`
> and Alembic revisions `0001`/`0003` instead.

This document describes everything added or modified after the FastAPI backend setup merge: the full SQLAlchemy ORM layer, Alembic migrations, metadata tests, and supporting configuration updates.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [What Changed (File Inventory)](#what-changed-file-inventory)
3. [Architecture Overview](#architecture-overview)
4. [How It Works](#how-it-works)
5. [Database Tables and Relationships](#database-tables-and-relationships)
6. [Alembic Migration Strategy](#alembic-migration-strategy)
7. [Testing](#testing)
8. [Developer Workflows](#developer-workflows)
9. [Modified Files (Diff Summary)](#modified-files-diff-summary)
10. [Full Source Code — All New Files](#full-source-code--all-new-files)

---

## Executive Summary

Before this work, the backend had FastAPI scaffolding, database session helpers, and an empty Alembic environment with placeholder model imports. **No SQLAlchemy models or migration revisions existed.**

This change set adds:

| Area | What was added |
|---|---|
| **ORM models** | 8 tables + 5 Postgres enum types under `backend/app/models/` |
| **Migrations** | `0001_baseline_existing_schema` (creates full schema) and `0002_queue_indexes_drop_queue_position` (indexes + drops legacy column) |
| **Alembic wiring** | `alembic/env.py` imports all models so autogenerate sees `Base.metadata` |
| **Tests** | `test_schema_metadata.py` (13 metadata contract tests, no DB required) and `test_alembic_smoke.py` (optional live migration smoke) |
| **Docs** | Expanded `backend/README.md` migration section; this changelog |

**Key design decision:** Models reflect **Alembic head** (`0002`), not the current live Supabase snapshot. Live Supabase still has `print_jobs.queue_position` and is missing Phase B indexes. Use `alembic stamp 0001` on existing Supabase; apply `0002` only after team approval.

**Test result (local):** `pytest tests/test_schema_metadata.py tests/test_health.py -v` → **16 passed**

---

## What Changed (File Inventory)

### New files (untracked)

```
backend/app/models/__init__.py
backend/app/models/enums.py
backend/app/models/user.py
backend/app/models/material.py
backend/app/models/printer.py
backend/app/models/print_job.py
backend/app/models/job_validation.py
backend/app/models/notification.py
backend/app/models/collection_record.py
backend/app/models/maintenance_log.py
backend/alembic/versions/0001_baseline_existing_schema.py
backend/alembic/versions/0002_queue_indexes_drop_queue_position.py
backend/tests/test_schema_metadata.py
backend/tests/test_alembic_smoke.py
Docs/Guides/database_schema.md          (design reference; predates models)
```

### Modified files (tracked, unstaged)

| File | Change |
|---|---|
| `backend/alembic/env.py` | Imports all model classes so Alembic autogenerate registers every table |
| `backend/README.md` | Documents fresh DB vs existing Supabase stamp/upgrade workflows |
| `.gitignore` | Adds `AGENTS.md` and `skills-lock.json` |

### Unchanged but used by this work

| File | Role |
|---|---|
| `backend/app/db/base.py` | `DeclarativeBase` with naming convention for constraints |
| `backend/app/db/session.py` | Engine + `SessionLocal` + `get_db()` FastAPI dependency |
| `backend/app/core/config.py` | Supplies `DATABASE_URL` to Alembic and the engine |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI (future routes)                   │
│                              │                                   │
│                              ▼                                   │
│                    get_db() → SessionLocal                       │
│                              │                                   │
│                              ▼                                   │
│              SQLAlchemy ORM models (app/models/*)                │
│                              │                                   │
│                              ▼                                   │
│         Base.metadata  ←──  Alembic env.py imports models      │
│                              │                                   │
│              ┌───────────────┴───────────────┐                 │
│              ▼                               ▼                   │
│     test_schema_metadata.py          alembic upgrade head        │
│     (metadata-only, no DB)           (disposable Postgres)       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    Supabase PostgreSQL
                    (managed Postgres)
```

**Stack:** Python 3.11+, SQLAlchemy 2.x declarative style (`Mapped`, `mapped_column`), native Postgres ENUM types, UUID primary keys with `gen_random_uuid()`, timezone-aware timestamps.

---

## How It Works

### 1. Declarative base (`app/db/base.py`)

All models inherit from `Base`, which uses a **naming convention** for auto-generated constraint names. This helps Alembic `--autogenerate` produce predictable migration scripts.

### 2. Enum layer (`app/models/enums.py`)

Python `enum.Enum` subclasses mirror Postgres enum types:

- `user_role` → `UserRole`
- `printer_status` → `PrinterStatus`
- `job_status` → `JobStatus`
- `check_type` → `CheckType`
- `notification_type` → `NotificationType`

The helper `_pg_enum()` wraps `sqlalchemy.Enum` with:

- `native_enum=True` — uses Postgres ENUM, not a CHECK constraint
- `values_callable` — stores lowercase string values (`student_staff`, not `STUDENT_STAFF`)
- `create_type=True` — ORM can create types when generating DDL from models

### 3. Model modules

Each table lives in its own module. Models define:

- **Columns** with `Mapped[T]` type hints
- **Constraints** via `__table_args__` (PK, unique, indexes) matching live Supabase names
- **Foreign keys** with explicit constraint names (e.g. `print_jobs_user_id_fkey`)
- **Relationships** with `back_populates` for bidirectional navigation
- **`TYPE_CHECKING` imports** to avoid circular import issues at runtime

### 4. Package export (`app/models/__init__.py`)

Re-exports all models and enums. Importing from `app.models` registers every table on `Base.metadata`.

### 5. Alembic integration (`alembic/env.py`)

On startup, Alembic:

1. Loads `settings.database_url` from environment
2. Sets `target_metadata = Base.metadata`
3. Side-effect imports of all models populate metadata before autogenerate or offline SQL generation

### 6. Two-phase migrations

| Revision | Purpose |
|---|---|
| `0001_baseline_existing_schema` | Creates all tables, enums, baseline indexes. Includes `queue_position` on `print_jobs` to match **historical** live Supabase |
| `0002_queue_indexes_drop_queue_position` | Adds performance indexes (FK lookups, partial queue index) and **drops** `queue_position` — queue order is derived from `submitted_at` for `submitted`/`queued` jobs |

**Models match head (`0002`):** no `queue_position` column; Phase B indexes are declared in model `__table_args__`.

---

## Database Tables and Relationships

### Entity-relationship diagram

```
users ─────────────┬──────────────── print_jobs ─────┬── job_validations
  │                │         │    │    │              ├── notifications
  │                │         │    │    │              └── collection_records (1:1)
  │                │         │    │    │
  │                │    printers ──┘    └── materials
  │                │         │
  │                │         └── maintenance_logs
  │                │
  ├── notifications
  ├── collection_records (as farmer)
  └── maintenance_logs (as farmer)
```

### Table summary

| Table | Primary purpose |
|---|---|
| `users` | Authentication identity, RBAC role, student/staff metadata |
| `materials` | Filament catalog (type, colour); colour is not a validation gate |
| `printers` | Physical printer registry, status, bed size, locked profile JSONB |
| `print_jobs` | Core job lifecycle: upload path, status, estimates, assignment |
| `job_validations` | Per-check validation results separate from extracted G-code metadata |
| `notifications` | User notifications tied to jobs (nullable `job_id` for system messages) |
| `collection_records` | Farmer workflow: ready → removed → collected timestamps |
| `maintenance_logs` | Farmer-recorded printer maintenance history |

### Important column semantics

| Column | Notes |
|---|---|
| `print_jobs.printer_id` | Nullable until a printer is assigned |
| `print_jobs.status` | Defaults to `submitted`; queue uses partial index on `submitted_at` where status ∈ `{submitted, queued}` |
| `print_jobs.est_*` vs validations | Estimates come from G-code parsing; validations are pass/fail checks |
| `users.unit_code` | Nullable — farmers/admins may not belong to a teaching unit |
| `printers.locked_profile` | JSONB — printer-locked slicer config |
| `collection_records.job_id` | Unique — one collection record per job |

### Indexes (Alembic head)

**Baseline (0001):**

- `idx_print_jobs_user_id`, `idx_print_jobs_printer_id`, `idx_print_jobs_status`
- `idx_job_validations_job_id`
- `idx_notifications_user_id`, `idx_notifications_user_is_read`
- `idx_collection_records_job_id`
- `idx_maintenance_logs_printer_id`

**Phase B (0002):**

- `idx_printers_current_material_id`
- `idx_print_jobs_material_id`
- `idx_notifications_job_id`
- `idx_collection_records_farmer_id`
- `idx_maintenance_logs_farmer_id`
- `idx_print_jobs_queue_submitted_at` — **partial index**: `WHERE status IN ('submitted', 'queued')`

---

## Alembic Migration Strategy

### Fresh local database

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

Creates all objects and sets version to `0002_queue_indexes_drop_queue_position`.

### Existing Supabase (schema already live)

**Do not** run `upgrade` from scratch — tables already exist.

```bash
cd backend && source .venv/bin/activate
alembic stamp 0001_baseline_existing_schema
```

This records baseline revision without running DDL. Live DB still has `queue_position`.

When Phase B is approved for that database:

```bash
alembic upgrade head
```

### Autogenerate new revisions

After model changes:

```bash
alembic revision --autogenerate -m "describe the change"
```

Always review generated SQL before applying.

---

## Testing

### Metadata contract tests (`test_schema_metadata.py`)

Runs **without a database**. Inspects `Base.metadata` only.

| Test | What it verifies |
|---|---|
| `test_all_expected_tables_registered` | All 8 tables present |
| `test_users_email_unique_and_unit_code_nullable` | Email unique, unit_code nullable |
| `test_print_jobs_nullability_and_no_queue_position` | Head schema has no `queue_position` |
| `test_notifications_job_id_nullable` | job_id optional |
| `test_collection_records_job_id_unique` | One record per job |
| `test_printer_locked_profile_and_validation_message_nullable` | JSONB and message nullable |
| `test_collection_timestamp_columns_nullable` | Farmer workflow timestamps optional |
| `test_enum_names_and_values` | All enum members and Postgres type names |
| `test_baseline_indexes_present_in_metadata` | 0001 indexes in models |
| `test_phase_b_indexes_present_in_metadata` | 0002 indexes in models |
| `test_explicit_fk_constraint_names` | Named FKs on print_jobs |
| `test_mapper_configuration_loads` | Relationships resolve without import errors |
| `test_baseline_revision_still_creates_queue_position` | Migration files stay consistent |

### Alembic smoke test (`test_alembic_smoke.py`)

**Skipped by default.** Enable only against disposable Postgres:

```bash
RUN_ALEMBIC_SMOKE=1 DATABASE_URL=postgresql+psycopg://... pytest tests/test_alembic_smoke.py -v
```

Safety guards:

- Skipped unless `RUN_ALEMBIC_SMOKE=1`
- **Fails** if URL contains `supabase.co`
- Drops/recreates `public` schema, runs `upgrade head`, asserts tables and version `0002`

---

## Developer Workflows

### Run all tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

### Use models in future service code (example)

```python
from sqlalchemy.orm import Session
from app.models import PrintJob, JobStatus

def get_queued_jobs(db: Session) -> list[PrintJob]:
    return (
        db.query(PrintJob)
        .filter(PrintJob.status == JobStatus.QUEUED)
        .order_by(PrintJob.submitted_at)
        .all()
    )
```

### What is **not** implemented yet

These models are schema-only. No API routes, services, or CRUD endpoints use them yet. The health check and OpenAPI docs from PR #27 still work unchanged.

---

## Modified Files (Diff Summary)

### `backend/alembic/env.py`

**Before:** Commented placeholder for future model imports.  
**After:** Imports `CollectionRecord`, `JobValidation`, `MaintenanceLog`, `Material`, `Notification`, `PrintJob`, `Printer`, `User` so `Base.metadata` is complete.

### `backend/README.md`

Added sections:

- Link to `Docs/Guides/database_schema.md`
- Fresh local DB: `alembic upgrade head`
- Existing Supabase: `alembic stamp 0001_baseline_existing_schema` (not `stamp head`)
- Phase B approval workflow
- Optional alembic smoke test command
- Updated project structure to show `app/models/`

### `.gitignore`

Added `AGENTS.md` and `skills-lock.json`.

---

## Full Source Code — All New Files

Below is the complete source of every new Python file in this change set.

---

### `backend/app/models/__init__.py`

```python
"""SQLAlchemy models matching the print-farm schema (Alembic head)."""

from app.models.collection_record import CollectionRecord
from app.models.enums import (
    CheckType,
    JobStatus,
    NotificationType,
    PrinterStatus,
    UserRole,
)
from app.models.job_validation import JobValidation
from app.models.maintenance_log import MaintenanceLog
from app.models.material import Material
from app.models.notification import Notification
from app.models.print_job import PrintJob
from app.models.printer import Printer
from app.models.user import User

__all__ = [
    "CheckType",
    "CollectionRecord",
    "JobStatus",
    "JobValidation",
    "MaintenanceLog",
    "Material",
    "Notification",
    "NotificationType",
    "PrintJob",
    "Printer",
    "PrinterStatus",
    "User",
    "UserRole",
]
```

**What it does:** Central import point. Any code doing `from app.models import PrintJob` gets the full model graph registered on `Base.metadata`.

---

### `backend/app/models/enums.py`

```python
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
```

**What it does:** Defines domain enums for RBAC, printer state, job lifecycle, validation check types, and notification types. Exports SQLAlchemy `Enum` column types bound to Postgres native enums.

---

### `backend/app/models/user.py`

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, PrimaryKeyConstraint, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UserRole, user_role_enum

if TYPE_CHECKING:
    from app.models.collection_record import CollectionRecord
    from app.models.maintenance_log import MaintenanceLog
    from app.models.notification import Notification
    from app.models.print_job import PrintJob


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="users_pkey"),
        UniqueConstraint("email", name="users_email_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    student_staff_number: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        user_role_enum,
        nullable=False,
        server_default=text("'student_staff'::user_role"),
    )
    unit_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    auth_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    print_jobs: Mapped[list[PrintJob]] = relationship(back_populates="user")
    notifications: Mapped[list[Notification]] = relationship(back_populates="user")
    collection_records: Mapped[list[CollectionRecord]] = relationship(
        back_populates="farmer",
    )
    maintenance_logs: Mapped[list[MaintenanceLog]] = relationship(
        back_populates="farmer",
    )
```

**What it does:** Maps the `users` table. Supports student/staff/farmer/admin roles. Relationships to jobs they submitted, notifications they receive, and farmer actions (collection, maintenance).

---

### `backend/app/models/material.py`

```python
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import PrimaryKeyConstraint, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.print_job import PrintJob
    from app.models.printer import Printer


class Material(Base):
    __tablename__ = "materials"
    __table_args__ = (PrimaryKeyConstraint("id", name="materials_pkey"),)

    id: Mapped[uuid.UUID] = mapped_column(
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    colour: Mapped[str] = mapped_column(Text, nullable=False)

    printers: Mapped[list[Printer]] = relationship(back_populates="current_material")
    print_jobs: Mapped[list[PrintJob]] = relationship(back_populates="material")
```

**What it does:** Filament/material catalog. Linked to printers (current loadout) and print jobs (requested material).

---

### `backend/app/models/printer.py`

```python
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, PrimaryKeyConstraint, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PrinterStatus, printer_status_enum

if TYPE_CHECKING:
    from app.models.maintenance_log import MaintenanceLog
    from app.models.material import Material
    from app.models.print_job import PrintJob


class Printer(Base):
    __tablename__ = "printers"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="printers_pkey"),
        Index("idx_printers_current_material_id", "current_material_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        server_default=text("gen_random_uuid()"),
    )
    model: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[PrinterStatus] = mapped_column(
        printer_status_enum,
        nullable=False,
        server_default=text("'idle'::printer_status"),
    )
    bed_size: Mapped[str] = mapped_column(Text, nullable=False)
    locked_profile: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    current_material_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("materials.id", name="printers_current_material_id_fkey"),
        nullable=True,
    )
    location: Mapped[str] = mapped_column(Text, nullable=False)

    current_material: Mapped[Material | None] = relationship(back_populates="printers")
    print_jobs: Mapped[list[PrintJob]] = relationship(back_populates="printer")
    maintenance_logs: Mapped[list[MaintenanceLog]] = relationship(
        back_populates="printer",
    )
```

**What it does:** Printer registry with operational status, physical location, bed size, optional locked slicer profile (JSONB), and current material FK. Phase B index on `current_material_id`.

---

### `backend/app/models/print_job.py`

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import JobStatus, job_status_enum

if TYPE_CHECKING:
    from app.models.collection_record import CollectionRecord
    from app.models.job_validation import JobValidation
    from app.models.material import Material
    from app.models.notification import Notification
    from app.models.printer import Printer
    from app.models.user import User


class PrintJob(Base):
    __tablename__ = "print_jobs"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="print_jobs_pkey"),
        Index("idx_print_jobs_user_id", "user_id"),
        Index("idx_print_jobs_printer_id", "printer_id"),
        Index("idx_print_jobs_status", "status"),
        Index("idx_print_jobs_material_id", "material_id"),
        Index(
            "idx_print_jobs_queue_submitted_at",
            "submitted_at",
            postgresql_where=text("status IN ('submitted', 'queued')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", name="print_jobs_user_id_fkey"),
        nullable=False,
    )
    printer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("printers.id", name="print_jobs_printer_id_fkey"),
        nullable=True,
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("materials.id", name="print_jobs_material_id_fkey"),
        nullable=False,
    )
    gcode_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        job_status_enum,
        nullable=False,
        server_default=text("'submitted'::job_status"),
    )
    est_duration_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    est_filament_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_duration_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_filament_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped[User] = relationship(back_populates="print_jobs")
    printer: Mapped[Printer | None] = relationship(back_populates="print_jobs")
    material: Mapped[Material] = relationship(back_populates="print_jobs")
    validations: Mapped[list[JobValidation]] = relationship(back_populates="job")
    notifications: Mapped[list[Notification]] = relationship(back_populates="job")
    collection_record: Mapped[CollectionRecord | None] = relationship(
        back_populates="job",
        uselist=False,
    )
```

**What it does:** Central job entity. Tracks G-code storage path, lifecycle status, estimated/actual print metrics, optional printer assignment, and links to validations, notifications, and collection workflow. **No `queue_position`** — FCFS queue uses `submitted_at` with partial index.

---

### `backend/app/models/job_validation.py`

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, PrimaryKeyConstraint, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CheckType, check_type_enum

if TYPE_CHECKING:
    from app.models.print_job import PrintJob


class JobValidation(Base):
    __tablename__ = "job_validations"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="job_validations_pkey"),
        Index("idx_job_validations_job_id", "job_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        server_default=text("gen_random_uuid()"),
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("print_jobs.id", name="job_validations_job_id_fkey"),
        nullable=False,
    )
    check_type: Mapped[CheckType] = mapped_column(check_type_enum, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    job: Mapped[PrintJob] = relationship(back_populates="validations")
```

**What it does:** Stores individual validation check results (printer/material/bed/config compatibility) separately from G-code extracted metadata on `print_jobs`.

---

### `backend/app/models/notification.py`

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, PrimaryKeyConstraint, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import NotificationType, notification_type_enum

if TYPE_CHECKING:
    from app.models.print_job import PrintJob
    from app.models.user import User


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="notifications_pkey"),
        Index("idx_notifications_user_id", "user_id"),
        Index("idx_notifications_user_is_read", "user_id", "is_read"),
        Index("idx_notifications_job_id", "job_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", name="notifications_user_id_fkey"),
        nullable=False,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("print_jobs.id", name="notifications_job_id_fkey"),
        nullable=True,
    )
    type: Mapped[NotificationType] = mapped_column(
        notification_type_enum,
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    user: Mapped[User] = relationship(back_populates="notifications")
    job: Mapped[PrintJob | None] = relationship(back_populates="notifications")
```

**What it does:** User notification inbox. Composite index on `(user_id, is_read)` for unread counts. Optional job FK for job-related events.

---

### `backend/app/models/collection_record.py`

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.print_job import PrintJob
    from app.models.user import User


class CollectionRecord(Base):
    __tablename__ = "collection_records"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="collection_records_pkey"),
        UniqueConstraint("job_id", name="collection_records_job_id_key"),
        # Redundant with the unique constraint; kept to match live Supabase.
        Index("idx_collection_records_job_id", "job_id"),
        Index("idx_collection_records_farmer_id", "farmer_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        server_default=text("gen_random_uuid()"),
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("print_jobs.id", name="collection_records_job_id_fkey"),
        nullable=False,
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", name="collection_records_farmer_id_fkey"),
        nullable=False,
    )
    ready_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    removed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    collected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped[PrintJob] = relationship(back_populates="collection_record")
    farmer: Mapped[User] = relationship(back_populates="collection_records")
```

**What it does:** Farmer collection workflow audit trail. One record per job (unique `job_id`). Tracks ready → removed → collected timestamps and optional notes.

---

### `backend/app/models/maintenance_log.py`

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, PrimaryKeyConstraint, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.printer import Printer
    from app.models.user import User


class MaintenanceLog(Base):
    __tablename__ = "maintenance_logs"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="maintenance_logs_pkey"),
        Index("idx_maintenance_logs_printer_id", "printer_id"),
        Index("idx_maintenance_logs_farmer_id", "farmer_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        server_default=text("gen_random_uuid()"),
    )
    printer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("printers.id", name="maintenance_logs_printer_id_fkey"),
        nullable=False,
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", name="maintenance_logs_farmer_id_fkey"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    printer: Mapped[Printer] = relationship(back_populates="maintenance_logs")
    farmer: Mapped[User] = relationship(back_populates="maintenance_logs")
```

**What it does:** Records printer maintenance events logged by farmers.

---

### `backend/alembic/versions/0001_baseline_existing_schema.py`

```python
"""Baseline schema matching the existing live Supabase database.

Fresh local databases apply this via ``alembic upgrade``. Existing Supabase
databases that already have these objects should use ``alembic stamp`` — do not
run ``upgrade`` against them for this revision.

RLS is enabled on live tables with zero policies; this revision does not
enable/disable RLS or invent policies (separate security follow-up).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_baseline_existing_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = postgresql.ENUM(
    "student_staff",
    "farmer",
    "admin",
    name="user_role",
    create_type=False,
)
printer_status = postgresql.ENUM(
    "idle",
    "printing",
    "error",
    "offline",
    "maintenance",
    name="printer_status",
    create_type=False,
)
job_status = postgresql.ENUM(
    "submitted",
    "queued",
    "printing",
    "completed",
    "failed",
    "removed",
    "ready_for_collection",
    name="job_status",
    create_type=False,
)
check_type = postgresql.ENUM(
    "printer_compatibility",
    "material_compatibility",
    "bed_size",
    "config",
    name="check_type",
    create_type=False,
)
notification_type = postgresql.ENUM(
    "job_started",
    "job_completed",
    "job_error",
    "ready_for_collection",
    name="notification_type",
    create_type=False,
)


def upgrade() -> None:
    user_role.create(op.get_bind(), checkfirst=True)
    printer_status.create(op.get_bind(), checkfirst=True)
    job_status.create(op.get_bind(), checkfirst=True)
    check_type.create(op.get_bind(), checkfirst=True)
    notification_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("student_staff_number", sa.Text(), nullable=False),
        sa.Column(
            "role",
            user_role,
            server_default=sa.text("'student_staff'::user_role"),
            nullable=False,
        ),
        sa.Column("unit_code", sa.Text(), nullable=True),
        sa.Column("auth_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="users_pkey"),
        sa.UniqueConstraint("email", name="users_email_key"),
    )

    op.create_table(
        "materials",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("colour", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="materials_pkey"),
    )

    op.create_table(
        "printers",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column(
            "status",
            printer_status,
            server_default=sa.text("'idle'::printer_status"),
            nullable=False,
        ),
        sa.Column("bed_size", sa.Text(), nullable=False),
        sa.Column("locked_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("current_material_id", sa.Uuid(), nullable=True),
        sa.Column("location", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["current_material_id"],
            ["materials.id"],
            name="printers_current_material_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id", name="printers_pkey"),
    )

    op.create_table(
        "print_jobs",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("printer_id", sa.Uuid(), nullable=True),
        sa.Column("material_id", sa.Uuid(), nullable=False),
        sa.Column("gcode_path", sa.Text(), nullable=False),
        sa.Column(
            "status",
            job_status,
            server_default=sa.text("'submitted'::job_status"),
            nullable=False,
        ),
        sa.Column("queue_position", sa.Integer(), nullable=True),
        sa.Column("est_duration_min", sa.Float(), nullable=True),
        sa.Column("est_filament_g", sa.Float(), nullable=True),
        sa.Column("actual_duration_min", sa.Float(), nullable=True),
        sa.Column("actual_filament_g", sa.Float(), nullable=True),
        sa.Column("unit_code", sa.Text(), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["materials.id"],
            name="print_jobs_material_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["printer_id"],
            ["printers.id"],
            name="print_jobs_printer_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="print_jobs_user_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id", name="print_jobs_pkey"),
    )
    op.create_index("idx_print_jobs_user_id", "print_jobs", ["user_id"], unique=False)
    op.create_index(
        "idx_print_jobs_printer_id",
        "print_jobs",
        ["printer_id"],
        unique=False,
    )
    op.create_index("idx_print_jobs_status", "print_jobs", ["status"], unique=False)

    op.create_table(
        "job_validations",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("check_type", check_type, nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["print_jobs.id"],
            name="job_validations_job_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id", name="job_validations_pkey"),
    )
    op.create_index(
        "idx_job_validations_job_id",
        "job_validations",
        ["job_id"],
        unique=False,
    )

    op.create_table(
        "notifications",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column("type", notification_type, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "is_read",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["print_jobs.id"],
            name="notifications_job_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="notifications_user_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id", name="notifications_pkey"),
    )
    op.create_index(
        "idx_notifications_user_id",
        "notifications",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "idx_notifications_user_is_read",
        "notifications",
        ["user_id", "is_read"],
        unique=False,
    )

    op.create_table(
        "collection_records",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("farmer_id", sa.Uuid(), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["farmer_id"],
            ["users.id"],
            name="collection_records_farmer_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["print_jobs.id"],
            name="collection_records_job_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id", name="collection_records_pkey"),
        sa.UniqueConstraint("job_id", name="collection_records_job_id_key"),
    )
    op.create_index(
        "idx_collection_records_job_id",
        "collection_records",
        ["job_id"],
        unique=False,
    )

    op.create_table(
        "maintenance_logs",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("printer_id", sa.Uuid(), nullable=False),
        sa.Column("farmer_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["farmer_id"],
            ["users.id"],
            name="maintenance_logs_farmer_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["printer_id"],
            ["printers.id"],
            name="maintenance_logs_printer_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id", name="maintenance_logs_pkey"),
    )
    op.create_index(
        "idx_maintenance_logs_printer_id",
        "maintenance_logs",
        ["printer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_maintenance_logs_printer_id", table_name="maintenance_logs")
    op.drop_table("maintenance_logs")

    op.drop_index("idx_collection_records_job_id", table_name="collection_records")
    op.drop_table("collection_records")

    op.drop_index("idx_notifications_user_is_read", table_name="notifications")
    op.drop_index("idx_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("idx_job_validations_job_id", table_name="job_validations")
    op.drop_table("job_validations")

    op.drop_index("idx_print_jobs_status", table_name="print_jobs")
    op.drop_index("idx_print_jobs_printer_id", table_name="print_jobs")
    op.drop_index("idx_print_jobs_user_id", table_name="print_jobs")
    op.drop_table("print_jobs")

    op.drop_table("printers")
    op.drop_table("materials")
    op.drop_table("users")

    notification_type.drop(op.get_bind(), checkfirst=True)
    check_type.drop(op.get_bind(), checkfirst=True)
    job_status.drop(op.get_bind(), checkfirst=True)
    printer_status.drop(op.get_bind(), checkfirst=True)
    user_role.drop(op.get_bind(), checkfirst=True)
```

**What it does:** Initial migration for greenfield databases. Creates all enums, 8 tables, baseline indexes. Includes legacy `queue_position` column to match historical Supabase snapshot.

---

### `backend/alembic/versions/0002_queue_indexes_drop_queue_position.py`

```python
"""Add missing FK/queue indexes and drop print_jobs.queue_position.

Apply only after the baseline revision is stamped on existing Supabase (or
upgraded on a fresh local database), and only after explicit approval for live.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_queue_indexes_drop_queue_position"
down_revision: Union[str, Sequence[str], None] = "0001_baseline_existing_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "idx_printers_current_material_id",
        "printers",
        ["current_material_id"],
        unique=False,
    )
    op.create_index(
        "idx_print_jobs_material_id",
        "print_jobs",
        ["material_id"],
        unique=False,
    )
    op.create_index(
        "idx_notifications_job_id",
        "notifications",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        "idx_collection_records_farmer_id",
        "collection_records",
        ["farmer_id"],
        unique=False,
    )
    op.create_index(
        "idx_maintenance_logs_farmer_id",
        "maintenance_logs",
        ["farmer_id"],
        unique=False,
    )
    op.create_index(
        "idx_print_jobs_queue_submitted_at",
        "print_jobs",
        ["submitted_at"],
        unique=False,
        postgresql_where=sa.text("status IN ('submitted', 'queued')"),
    )
    op.drop_column("print_jobs", "queue_position")


def downgrade() -> None:
    op.add_column(
        "print_jobs",
        sa.Column("queue_position", sa.Integer(), nullable=True),
    )
    op.drop_index(
        "idx_print_jobs_queue_submitted_at",
        table_name="print_jobs",
        postgresql_where=sa.text("status IN ('submitted', 'queued')"),
    )
    op.drop_index("idx_maintenance_logs_farmer_id", table_name="maintenance_logs")
    op.drop_index("idx_collection_records_farmer_id", table_name="collection_records")
    op.drop_index("idx_notifications_job_id", table_name="notifications")
    op.drop_index("idx_print_jobs_material_id", table_name="print_jobs")
    op.drop_index("idx_printers_current_material_id", table_name="printers")
```

**What it does:** Phase B schema improvements. Adds FK and queue indexes; removes redundant `queue_position` in favour of timestamp-based FCFS ordering.

---

### `backend/tests/test_schema_metadata.py`

```python
"""Metadata contract tests for SQLAlchemy models vs agreed live schema.

These tests inspect Base.metadata only — no database connection.
Models reflect Alembic head (after 0002): no queue_position; Phase B indexes present.
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


def test_users_email_unique_and_unit_code_nullable() -> None:
    users = _table("users")
    assert "users_email_key" in _unique_constraint_names("users")
    assert users.c.unit_code.nullable is True
    assert users.c.auth_hash.nullable is False
    assert users.c.email.nullable is False


def test_print_jobs_nullability_and_no_queue_position() -> None:
    jobs = _table("print_jobs")
    assert jobs.c.printer_id.nullable is True
    assert jobs.c.unit_code.nullable is True
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
    assert {m.value for m in UserRole} == {"student_staff", "farmer", "admin"}
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
    assert 'sa.Column("queue_position", sa.Integer(), nullable=True)' in baseline
    assert 'op.drop_column("print_jobs", "queue_position")' in followup
    assert 'revision: str = "0001_baseline_existing_schema"' in baseline
    assert 'revision: str = "0002_queue_indexes_drop_queue_position"' in followup
    assert 'down_revision' in followup and "0001_baseline_existing_schema" in followup
```

**What it does:** Fast, offline schema contract tests. Catches drift between models, migrations, and design decisions without needing Postgres.

---

### `backend/tests/test_alembic_smoke.py`

```python
"""Optional smoke: alembic upgrade head on an empty disposable Postgres.

Skipped unless RUN_ALEMBIC_SMOKE=1 and DATABASE_URL points at a disposable DB.
Never enable this against production Supabase.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_ALEMBIC_SMOKE") != "1",
    reason="Set RUN_ALEMBIC_SMOKE=1 with a disposable DATABASE_URL to run",
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_alembic_upgrade_head_on_empty_database() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for alembic smoke")

    # Refuse obvious hosted Supabase URLs even if the flag is set.
    if "supabase.co" in database_url:
        pytest.fail("Refusing alembic smoke against a Supabase URL")

    engine = create_engine(database_url)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(cfg, "head")

    with engine.connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                )
            )
        }
        assert {
            "users",
            "materials",
            "printers",
            "print_jobs",
            "job_validations",
            "notifications",
            "collection_records",
            "maintenance_logs",
            "alembic_version",
        } <= tables

        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert version == "0002_queue_indexes_drop_queue_position"

        cols = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'print_jobs'"
                )
            )
        }
        assert "queue_position" not in cols
```

**What it does:** End-to-end migration verification on throwaway Postgres. Guarded behind env flag and Supabase URL rejection.

---

### Modified: `backend/alembic/env.py` (full current file)

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.base import Base

# Import all models so Base.metadata includes every table for autogenerate.
from app.models import (  # noqa: F401
    CollectionRecord,
    JobValidation,
    MaintenanceLog,
    Material,
    Notification,
    PrintJob,
    Printer,
    User,
)

config = context.config

# Override the sqlalchemy.url from environment settings.
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode (generates SQL without connecting)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

---

## Related Documentation

- Design proposal: [`database_schema.md`](./database_schema.md)
- Backend setup and commands: [`../../backend/README.md`](../../backend/README.md)
- MVP scope: [`../Assignment1/Assignment1.md`](../Assignment1/Assignment1.md)

---

## Next Steps (Not in This Change Set)

1. Wire models into FastAPI routes and service layer (auth, upload, queue dispatch)
2. Apply `alembic stamp 0001` on team Supabase instance
3. Team approval for Phase B (`0002`) on live database
4. RLS policies (live tables have RLS enabled with zero policies today)
5. Pydantic schemas for API request/response shapes derived from these models
