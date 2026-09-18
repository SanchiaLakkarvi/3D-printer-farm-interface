# 3D Printer Farm Management System — Database Schema

**Database:** PostgreSQL
**ORM:** SQLAlchemy or SQLModel (FastAPI backend)

This schema supports the agreed MVP: authentication and role-based access control, G-code upload and validation, compatible-printer selection, compatibility-aware queue management, print-job tracking, notifications, the Farmer collection workflow, and basic usage reporting.

---

## Entity-Relationship Overview

```
USERS ||--o{ PRINT_JOBS        : submits
USERS ||--o{ NOTIFICATIONS     : receives
USERS ||--o{ COLLECTION_RECORDS : "actioned by (farmer)"
USERS ||--o{ MAINTENANCE_LOGS  : "logged by (farmer)"
PRINTERS ||--o{ PRINT_JOBS     : processes
PRINTERS ||--o{ MAINTENANCE_LOGS : has
MATERIALS ||--o{ PRINT_JOBS    : uses
PRINT_JOBS ||--o{ JOB_VALIDATIONS : "checked by"
PRINT_JOBS ||--o{ NOTIFICATIONS   : triggers
PRINT_JOBS ||--o| COLLECTION_RECORDS : has
```

---

## Tables

### `users`

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | Same UUID as Supabase Auth user id |
| `email` | `string`, unique | Login identifier |
| `first_name` | `string` | |
| `last_name` | `string` | |
| `student_number` | `string`, nullable | Required for Role `student` (derived from Student Email); null for Farmer/Admin |
| `role` | `enum` | `student`, `farmer`, `admin` |
| `department` | `string`, nullable | User's department for admin cost/usage reporting, e.g. `engineering`, `IT`, `mechanical`. Nullable since farmers/admins (and some staff) may not belong to a single department |
| `created_at` | `timestamp` | |

Credentials and sessions live in Supabase Auth; this table does not store password hashes.

### `printers`

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `model` | `string` | e.g. Prusa XL, Prusa CORE One |
| `status` | `enum` | `idle`, `printing`, `error`, `offline`, `maintenance` |
| `bed_size` | `string` | |
| `locked_profile` | `jsonb` | Locked config: material, bed size, printer profile |
| `current_material_id` | `uuid` FK → `materials.id` | Nullable |
| `location` | `string` | |

### `materials`

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `name` | `string` | |
| `type` | `string` | e.g. PLA, PETG |
| `colour` | `string` | Not used as a validation condition (colour availability changes) |

### `print_jobs`

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `user_id` | `uuid` FK → `users.id` | |
| `printer_id` | `uuid` FK → `printers.id` | Nullable until assigned |
| `material_id` | `uuid` FK → `materials.id` | |
| `gcode_path` | `string` | Path/reference to uploaded file |
| `status` | `enum` | `submitted`, `queued`, `printing`, `completed`, `failed`, `removed`, `ready_for_collection` |
| `queue_position` | `int` | Scoped per compatible printer/printer group (see note below) |
| `est_duration_min` | `float` | Extracted from G-code metadata |
| `est_filament_g` | `float` | Extracted from G-code metadata |
| `actual_duration_min` | `float` | Recorded after completion |
| `actual_filament_g` | `float` | Recorded after completion |
| `department` | `string`, nullable | For usage/cost reporting by department (may differ from the user's profile department) |
| `submitted_at` | `timestamp` | |
| `completed_at` | `timestamp` | |

### `job_validations`

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `job_id` | `uuid` FK → `print_jobs.id` | |
| `check_type` | `enum` | `printer_compatibility`, `material_compatibility`, `bed_size`, `config` |
| `passed` | `boolean` | |
| `message` | `string` | |
| `checked_at` | `timestamp` | |

### `notifications`

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `user_id` | `uuid` FK → `users.id` | |
| `job_id` | `uuid` FK → `print_jobs.id` | Nullable |
| `type` | `enum` | `job_started`, `job_completed`, `job_error`, `ready_for_collection` |
| `message` | `string` | |
| `is_read` | `boolean` | |
| `sent_at` | `timestamp` | |

### `collection_records`

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `job_id` | `uuid` FK → `print_jobs.id`, unique | One-to-one with job |
| `farmer_id` | `uuid` FK → `users.id` | |
| `ready_at` | `timestamp` | |
| `removed_at` | `timestamp` | |
| `collected_at` | `timestamp` | |
| `notes` | `string` | |

### `maintenance_logs`

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `printer_id` | `uuid` FK → `printers.id` | |
| `farmer_id` | `uuid` FK → `users.id` | |
| `description` | `string` | |
| `created_at` | `timestamp` | |

---

## Design Notes

**Core entity choices**
- `users.department` is nullable rather than a separate `departments` table — admins need cost/usage reporting *by* department (e.g. engineering, IT, mechanical), not a full department-management system. A plain nullable string column is enough to filter/group reports. It's nullable because farmers and admins, and possibly some staff, aren't tied to a single department.
- `print_jobs.department` is kept as well, since a student may print for a different department than the one on their profile. In practice the job-level field can default to `users.department` at submission time but remain overridable per job — this keeps per-job reporting accurate even if a user's profile department changes later or a job doesn't match their default.
- `users.role` is a single enum (`student`, `farmer`, `admin`) rather than a separate roles/permissions table — the MVP only needs three fixed roles, so RBAC logic can live in FastAPI dependency checks rather than a join table. This can be migrated to a full roles/permissions join table later if finer-grained access control is needed. Higher Roles retain lower capabilities on the same profile (Admin ⊃ Farmer ⊃ submit).
- `users.student_number` is nullable so Farmers and Admins are not forced to invent a student id; Students get the value derived from the Student Email local-part at Sign-up.
- `printers.locked_profile` is a `jsonb` column holding the compatibility config (material, bed size, printer profile). Postgres's native JSON support (a reason the team selected it in Section 4.1.3) allows this to be stored and queried without a rigid separate table per config field.
- `materials` is its own table rather than a string on `printers`/`print_jobs` because lifetime and per-material usage stats are required (Section 1.2) — usage is aggregated from `print_jobs` grouped by `material_id`.

**Workflow-critical separations**
- `job_validations` is split out from `print_jobs` because the assignment explicitly separates "validation conditions" from "extracted metadata" (Section 2.3). One job can have several validation checks (profile, material, bed size, config), each independently pass/fail — this doesn't map cleanly onto flat columns on `print_jobs`.
- `collection_records` is separate from `print_jobs` status because the Farmer collection workflow (ready → removed → collected) has its own timestamps and an owner (`farmer_id`) distinct from the job's submitter. Keeping it separate also simplifies the Farmer's "completed jobs" view.
- `notifications` references both `user_id` and `job_id` so the system can notify on start/complete/error, and could support farmer-facing notifications later without schema changes.

**What's deliberately not modelled yet**
- No `payments`/`pricing` table — the cost model isn't confirmed (Section 4.2, open decisions). Add a `cost_estimate` column to `print_jobs` once pricing rules are agreed with the client.
- No `approval_requests` table — same reason (User Story 8 is explicitly not committed scope until the client confirms thresholds).
- "Basic usage reporting" is better served by SQL views/aggregates over `print_jobs` + `materials` (e.g. `SUM(actual_duration_min) GROUP BY user_id`, `department`, `printer_id`) rather than a separate reporting table, to avoid data duplication and staleness.

**Open issue to resolve as a team**
`queue_position` on `print_jobs` is fine for MVP first-come-first-served, but the compatibility-aware queue rule (Section 3.4) means position should be scoped per printer-group, not global. Either:
- add a `printer_group_id` and make ordering `(printer_group_id, queue_position)`, or
- drop `queue_position` entirely and compute ordering on the fly from `submitted_at`, filtered to compatible printers — this avoids race conditions when jobs are reordered as printers free up.
