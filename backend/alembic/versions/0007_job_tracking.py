"""Merge the existing heads and add QR tracking and durable submission claims."""
import sqlalchemy as sa
from alembic import op

revision = "0007_job_tracking"
down_revision = (
    "0006_printer_prusalink_and_job_link",
    "0005_print_jobs_pending_selection_upload",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name in ("tracking_url", "qr_svg", "tracking_status", "request_fingerprint"):
        op.add_column("print_jobs", sa.Column(name, sa.Text(), nullable=True))
    op.add_column("print_jobs", sa.Column(
        "submission_id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")
    ))
    op.create_unique_constraint("uq_print_jobs_submission_id", "print_jobs", ["submission_id"])
    op.add_column("print_jobs", sa.Column(
        "submission_state", sa.Text(), nullable=False, server_default="pending"
    ))
    op.create_table(
        "job_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("print_jobs.id"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_job_events_job_id", "job_events", ["job_id"])
    op.execute("""UPDATE print_jobs SET tracking_url = '/api/jobs/' || id::text,
        tracking_status = upper(status::text),
        submission_state = CASE WHEN status::text IN
            ('printing', 'completed', 'failed', 'ready_for_collection', 'removed')
            OR printer_job_id IS NOT NULL OR started_at IS NOT NULL
            THEN 'submitted' ELSE 'pending' END""")
    # Historical transitions cannot be reconstructed; record only the known state.
    op.execute("""INSERT INTO job_events (job_id, status, occurred_at)
        SELECT id, tracking_status, now() FROM print_jobs""")


def downgrade() -> None:
    op.drop_table("job_events")
    op.drop_constraint("uq_print_jobs_submission_id", "print_jobs", type_="unique")
    for name in ("submission_state", "submission_id", "tracking_status", "qr_svg", "tracking_url", "request_fingerprint"):
        op.drop_column("print_jobs", name)
