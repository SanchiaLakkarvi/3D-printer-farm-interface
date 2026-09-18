"""Add PrusaLink connection columns to printers and printer_job_id to print_jobs.

printer_job_id is the job id the printer itself reports (PrusaLink job.id), used
to stop or track the job on the device.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_printer_prusalink_and_job_link"
down_revision: Union[str, Sequence[str], None] = "0005_job_timing_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for name in ("prusalink_url", "prusalink_username", "prusalink_password"):
        op.add_column("printers", sa.Column(name, sa.Text(), nullable=True))
    op.add_column("print_jobs", sa.Column("printer_job_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("print_jobs", "printer_job_id")
    for name in ("prusalink_password", "prusalink_username", "prusalink_url"):
        op.drop_column("printers", name)
