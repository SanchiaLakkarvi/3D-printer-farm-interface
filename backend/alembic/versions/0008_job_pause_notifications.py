"""Add pause/resume notification types and print_jobs.paused_at.

paused_at is set while the printer reports the job PAUSED, so the sync loop
notifies the owner once per pause and once on resume.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_job_pause_notifications"
down_revision: Union[str, Sequence[str], None] = "0007_merge_queue_upload"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'job_paused'")
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'job_resumed'")
    op.add_column(
        "print_jobs",
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    # Postgres cannot drop enum values; job_paused/job_resumed stay on the type.
    op.drop_column("print_jobs", "paused_at")
