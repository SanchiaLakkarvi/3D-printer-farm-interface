"""Rename users/print_jobs.unit_code to department (idempotent).

Department values (e.g. engineering, IT, mechanical) support admin
usage/cost reporting by faculty area rather than teaching unit codes.

Baseline 0001 now creates ``department`` directly. This revision remains so
databases created from an older 0001 (or live Supabase before the rename)
still converge. Safe to re-run when the column is already ``department``.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0003_rename_unit_code_to_department"
down_revision: Union[str, Sequence[str], None] = "0002_queue_indexes_drop_queue_position"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'users'
                  AND column_name = 'unit_code'
            ) THEN
                ALTER TABLE users RENAME COLUMN unit_code TO department;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'print_jobs'
                  AND column_name = 'unit_code'
            ) THEN
                ALTER TABLE print_jobs RENAME COLUMN unit_code TO department;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'users'
                  AND column_name = 'department'
            ) THEN
                ALTER TABLE users RENAME COLUMN department TO unit_code;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'print_jobs'
                  AND column_name = 'department'
            ) THEN
                ALTER TABLE print_jobs RENAME COLUMN department TO unit_code;
            END IF;
        END $$;
        """
    )
