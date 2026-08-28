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
        sa.Column("department", sa.Text(), nullable=True),
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
        sa.Column("department", sa.Text(), nullable=True),
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
