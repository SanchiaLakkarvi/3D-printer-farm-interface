"""Add the farmer-facing job-submitted notification type."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0009_job_submitted_notifications"
down_revision: Union[str, Sequence[str], None] = "0008_job_pause_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'job_submitted'")


def downgrade() -> None:
    # PostgreSQL cannot safely remove an enum value while rows may still use it.
    pass
