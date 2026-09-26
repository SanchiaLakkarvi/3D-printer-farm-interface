"""Add pending_selection status, nullable material_id, original_filename.

Supports G-code upload creating jobs before material inference / printer
selection. Queue eligibility remains submitted + queued only.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_print_jobs_pending_selection_upload"
down_revision: Union[str, Sequence[str], None] = "0004_users_auth_profile_supabase_model"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'pending_selection'")

    op.alter_column(
        "print_jobs",
        "material_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.add_column(
        "print_jobs",
        sa.Column("original_filename", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("print_jobs", "original_filename")
    op.alter_column(
        "print_jobs",
        "material_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    # Postgres cannot remove an enum label safely without recreating the type.
    # pending_selection remains on job_status after downgrade; rows must not
    # use it (callers should migrate them before downgrade).
