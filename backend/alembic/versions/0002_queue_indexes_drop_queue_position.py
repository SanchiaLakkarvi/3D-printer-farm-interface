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
