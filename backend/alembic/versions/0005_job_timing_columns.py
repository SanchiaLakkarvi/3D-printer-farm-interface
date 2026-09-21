"""Add job timing columns: started_at, est_start_at, est_completion_at.

started_at records when a job actually began printing so queue estimates
no longer assume it started at submission. est_* store the latest computed
schedule so it can be read without recomputation.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_job_timing_columns"
down_revision: Union[str, Sequence[str], None] = "0004_users_auth_profile_supabase_model"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for name in ("started_at", "est_start_at", "est_completion_at"):
        op.add_column("print_jobs", sa.Column(name, sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for name in ("est_completion_at", "est_start_at", "started_at"):
        op.drop_column("print_jobs", name)
