"""Merge printer queue and pending-selection upload migration branches."""

revision = "0007_merge_queue_upload"
down_revision = (
    "0006_printer_prusalink_and_job_link",
    "0005_print_jobs_pending_selection_upload",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
