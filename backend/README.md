# 3D Printer Farm — Backend

FastAPI backend for the UWA 3D Printer Farm Management System.

## Prerequisites

- Python 3.11+
- PostgreSQL (or Supabase)

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

Key settings:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (Supabase or local) |
| `AUTH_ADAPTER` | `fake` (local/tests) or `supabase` (real Auth) |
| `SUPABASE_URL` | Supabase project URL (server-only) |
| `SUPABASE_ANON_KEY` | Supabase anon key (server-only; used for Sign-up/Sign-in/token checks) |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (server-only; never expose to the browser; Seed/Admin user cleanup) |
| `JWT_SECRET_KEY` | Legacy placeholder; sessions come from Supabase Auth when `AUTH_ADAPTER=supabase` |
| `CORS_ORIGINS` | Allowed frontend origins (comma-separated; local Vite uses `http://localhost:5173`) |
| `MOCK_PRINTER_BASE_URL` | URL of the mock printer server |

When `AUTH_ADAPTER=supabase`, enable **Confirm email** in the Supabase Dashboard
(Authentication → Sign In / Providers → Email). Set Site URL to the UI origin
(e.g. `http://localhost:5173`) and allow that origin under Redirect URLs.

**Email OTP length must be 6.** In the same Email provider panel, set
**Email OTP Length** to `6` (not 8). The Confirm signup template and the UI both
expect a six-digit `{{ .Token }}`; an 8-digit project setting causes a mismatch.

Important: edit **Authentication → Email Templates → Confirm signup** so the
email shows the **6-digit OTP** (`{{ .Token }}`), **not** `{{ .ConfirmationURL }}`
(mail scanners often auto-open confirm links):

```html
<h2>Confirm your email</h2>
<p>Your UWA Print Farm verification code is:</p>
<p style="font-size:24px;letter-spacing:4px;"><strong>{{ .Token }}</strong></p>
<p>Enter this 6-digit code in the app to finish signup. It expires soon.</p>
```

Optional subject: `Your verification code is {{ .Token }}`. Do **not** include
`{{ .ConfirmationURL }}`. An optional non-confirming link may use `{{ .SiteURL }}`
only.

Students enter the code in the UI; FastAPI verifies via
`POST /api/auth/verify-signup-code` (GoTrue `POST /auth/v1/verify` with
`type=signup`, `email`, `token`). Resend uses `POST /api/auth/resend-signup-code`.
Verification does **not** create a session or `users` row — the profile is still
created on the first successful Sign-in after confirm.

`POST /api/auth/confirm-email` (`token_hash`) remains temporarily for legacy
links; the primary path is the 6-digit OTP.

**Brevo / SMTP:** Brevo is the SMTP relay only (configured under Supabase →
Project Settings → Authentication → SMTP). Supabase builds the Confirm signup
email from the template above; do **not** create a separate Brevo transactional
template for signup OTP. Turn off Brevo click/open tracking for this sender if
enabled, and keep the SMTP sender address aligned with an allowed Brevo sender.

### Demo Admin + Farmers

Demo Admin and Farmer accounts already exist in the shared Supabase project
(Auth + matching `users` profiles). Sign in via `POST /api/auth/signin` with
those credentials. To provision additional staff, create the Auth user in
Supabase and a matching `users` row with the same UUID (null `student_number`,
role `farmer` or `admin`) — this is not Student Sign-up.

## Run (without Docker)

```bash
uvicorn app.main:app --reload --port 8000
```

The API docs are available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Run with Docker

1. Copy `.env.example` → `.env` and fill Supabase values (`DATABASE_URL`,
   `AUTH_ADAPTER=supabase`, `SUPABASE_URL`, anon + service-role keys).
2. From the **repository root** (not `backend/`):

```bash
docker compose up --build
```

Compose loads `backend/.env` and starts the API (port 8000) plus the frontend
`web` service (port 5173). Postgres/Auth come from Supabase. Migrations do
**not** run on boot against the shared DB; set `RUN_MIGRATIONS=1` only for a
disposable database you intentionally want upgraded.

Useful URLs once up:

- UI: http://localhost:5173
- Health: http://localhost:8000/health
- Interactive docs (try endpoints): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Stop with `Ctrl+C`, or run detached with `docker compose up --build -d` and
stop with `docker compose down`.

## Auth endpoints

| Method | Path | Auth | Behaviour |
|---|---|---|---|
| `POST` | `/api/auth/signup` | public | Student Sign-up → pending (`message`, `email`); no profile yet |
| `POST` | `/api/auth/verify-signup-code` | public | Exchange emailed 6-digit OTP (`email` + `code`); no session/profile |
| `POST` | `/api/auth/resend-signup-code` | public | Resend signup OTP email (`email`) |
| `POST` | `/api/auth/confirm-email` | public | Legacy: exchange `token_hash` after explicit Confirm click |
| `POST` | `/api/auth/signin` | public | email + password → `access_token` + safe profile (creates student on first confirmed Sign-in) |
| `GET` | `/api/auth/me` | Bearer | profile for the token subject |
| `POST` | `/api/auth/signout` | public | `204`; no server session store |
| `GET` | `/api/rbac/farmer` | Bearer + Farmer | probe; Admin OK (Admin ⊃ Farmer); Student `403` |
| `GET`/`POST` | `/api/rbac/admin` | Bearer + Admin | probe; Farmer/Student `403`; POST body `role` ignored |
| `GET` | `/api/rbac/submit` | Bearer + submit | probe; Student/Farmer/Admin OK (hierarchy) |

## Job upload endpoints

| Method | Path | Auth | Behaviour |
|---|---|---|---|
| `POST` | `/api/jobs/upload` | Bearer + submit | Multipart field `file` (`.gcode` / `.gco`); creates Print Job in `pending_selection`; returns job id, status, original filename basename, relative `gcode_path` only |

Storage layout: `{FILE_STORAGE_ROOT}/{user_id}/{job_id}.(gcode|gco)`. Client filename/path is never used for disk location. `material_id` / `printer_id` / estimates stay unset until later slices. Gate rejects use structured codes (`INVALID_EXTENSION`, `FILE_TOO_LARGE`, `EMPTY_FILE`) and never create `pending_selection` jobs or write files. Write/DB failures return `UPLOAD_FAILED` after cleanup; responses never include absolute host paths or raw OS/DB errors. Content validation plugs into `upload_service.run_content_validation_hook` after the local gate (validate-then-commit); file delete-on-collect stays with the lifecycle slice.

## Material and Printer endpoints

| Method | Path | Auth | Behaviour |
|---|---|---|---|
| `GET` | `/api/materials` | Bearer | List all materials |
| `POST` | `/api/materials` | Bearer + Admin | Create a new material (`name`, `type`, `colour`) |
| `GET` | `/api/printers` | Bearer | List all printers with nested `current_material` |
| `GET` | `/api/printers/{id}` | Bearer | Get a single printer by ID |
| `POST` | `/api/printers` | Bearer + Admin | Create a new printer |
| `PATCH` | `/api/printers/{id}` | Bearer + Admin | Update status, material, location, or locked_profile |

### Seed Printers & Materials (demo hardware)

To populate local/staging databases with demo UWA printers (Prusa CORE One, Prusa XL) and materials (PLA, PETG):

```bash
cd backend && source .venv/bin/activate
python -m app.scripts.seed_printers
```

**Sign-out:** access tokens are provider JWTs (or fake tokens in tests). The API does not keep a server-side session list, so Sign-out is **client-side**: discard the stored `access_token`. Call `POST /signout` for a uniform API boundary; revoke/refresh-token logout can be added later if needed. Missing, invalid, or expired Bearer tokens on protected routes return `401`.

**RBAC:** Role always comes from the application profile after token validation. Client-supplied `role` query/body fields are ignored and cannot escalate privileges. Capability hierarchy: Admin ⊃ Farmer ⊃ submit. Use `require_farmer` / `require_admin` / `require_submitter` (or `require_roles(...)`) on real endpoints; the `/rbac/*` probes exist so authorization can be tested before other farm features land.

## Database Migrations

Schema design notes live in [`Docs/Guides/database_schema.md`](../Docs/Guides/database_schema.md).
SQLAlchemy models under `app/models/` mirror the **live** Supabase schema as the
baseline, then track approved Alembic revisions (currently through
`0002_queue_indexes_drop_queue_position`, then
`0003_rename_unit_code_to_department`, then
`0004_users_auth_profile_supabase_model`, then
`0005_print_jobs_pending_selection_upload`).

### Fresh local database

```bash
alembic upgrade head
```

### Existing Supabase (schema already created)

Do **not** run `alembic upgrade` against a database that already has the baseline
tables — that would try to recreate them. Stamp the **baseline** revision only
(live still has `queue_position` and does not yet have the Phase B indexes):

```bash
cd backend && source .venv/bin/activate && alembic stamp 0001_baseline_existing_schema
```

Optional checks before stamp:

```bash
alembic current
alembic history
```

After stamp, `alembic current` should show `0001_baseline_existing_schema`.
Do **not** `stamp head` while `0002_queue_indexes_drop_queue_position` remains
unapplied on that database.

When the team approves Phase B DDL for that database:

```bash
alembic upgrade head
```

### New revisions after model changes

```bash
alembic revision --autogenerate -m "describe the change"
```

Review generated migrations before applying. Never `upgrade` a DB that already
has the baseline objects unless the revision is known empty/no-op for that DB.
## Tests

```bash
pytest tests/ -v
```

Optional disposable-Postgres migration smoke (never against production Supabase):

```bash
RUN_ALEMBIC_SMOKE=1 DATABASE_URL=postgresql+psycopg://... pytest tests/test_alembic_smoke.py -v
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── api/                  # Route handlers
│   │   ├── router.py         # Central API router
│   │   └── v1/               # Versioned endpoints
│   ├── adapters/             # External ports (Auth, printers)
│   ├── core/                 # Config, security, shared utilities
│   │   ├── config.py         # Environment-based settings
│   │   └── exceptions.py     # Structured error classes
│   ├── db/                   # Database engine and session
│   │   ├── base.py           # SQLAlchemy declarative base
│   │   └── session.py        # Session factory and dependency
│   ├── services/             # Application services
│   └── models/               # SQLAlchemy models (live schema + approved diffs)
├── alembic/                  # Database migration scripts
├── tests/                    # pytest test suite
├── storage/                  # Uploaded G-code file storage
├── requirements.txt
├── .env.example
├── alembic.ini
└── Dockerfile
```
