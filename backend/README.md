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
| `JWT_SECRET_KEY` | Random secret for JWT signing |
| `CORS_ORIGINS` | Allowed frontend origins |
| `MOCK_PRINTER_BASE_URL` | URL of the mock printer server |

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

The API docs are available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Database Migrations

```bash
# Run all pending migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "describe the change"
```

## Tests

```bash
pytest tests/ -v
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── api/                  # Route handlers
│   │   ├── router.py         # Central API router
│   │   └── v1/               # Versioned endpoints
│   ├── core/                 # Config, security, shared utilities
│   │   ├── config.py         # Environment-based settings
│   │   └── exceptions.py     # Structured error classes
│   └── db/                   # Database engine and session
│       ├── base.py           # SQLAlchemy declarative base
│       └── session.py        # Session factory and dependency
├── alembic/                  # Database migration scripts
├── tests/                    # pytest test suite
├── storage/                  # Uploaded G-code file storage
├── requirements.txt
├── .env.example
├── alembic.ini
└── Dockerfile
```
