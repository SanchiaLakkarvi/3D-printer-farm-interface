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
        assert version == "0004_users_auth_profile_supabase_model"

        user_cols = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'users'"
                )
            )
        }
        assert {"first_name", "last_name", "student_number"} <= user_cols
        assert "auth_hash" not in user_cols
        assert "name" not in user_cols
        assert "student_staff_number" not in user_cols

        role_labels = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT e.enumlabel FROM pg_enum e "
                    "JOIN pg_type t ON e.enumtypid = t.oid "
                    "WHERE t.typname = 'user_role'"
                )
            )
        }
        assert role_labels == {"student", "farmer", "admin"}

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
