"""Align users profile with Supabase Auth model.

- Rename user_role enum value student_staff → student
- Replace name with first_name / last_name
- Rename student_staff_number → student_number (nullable)
- Drop auth_hash (credentials live in Supabase Auth only)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_users_auth_profile_supabase_model"
down_revision: Union[str, Sequence[str], None] = "0003_rename_unit_code_to_department"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Role default must move off the old enum label before rename.
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute("ALTER TYPE user_role RENAME VALUE 'student_staff' TO 'student'")
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'student'::user_role")

    op.add_column("users", sa.Column("first_name", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.Text(), nullable=True))
    op.execute(
        """
        UPDATE users
        SET
            first_name = CASE
                WHEN position(' ' IN name) > 0 THEN split_part(name, ' ', 1)
                ELSE name
            END,
            last_name = CASE
                WHEN position(' ' IN name) > 0 THEN substr(name, position(' ' IN name) + 1)
                ELSE ''
            END
        """
    )
    op.alter_column("users", "first_name", existing_type=sa.Text(), nullable=False)
    op.alter_column("users", "last_name", existing_type=sa.Text(), nullable=False)
    op.drop_column("users", "name")

    op.alter_column(
        "users",
        "student_staff_number",
        new_column_name="student_number",
        existing_type=sa.Text(),
        nullable=True,
    )

    op.drop_column("users", "auth_hash")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("auth_hash", sa.Text(), nullable=False, server_default=""),
    )
    op.alter_column("users", "auth_hash", server_default=None)

    # Restore non-null student id; empty string for staff rows that had NULL.
    op.execute(
        "UPDATE users SET student_number = '' WHERE student_number IS NULL"
    )
    op.alter_column(
        "users",
        "student_number",
        new_column_name="student_staff_number",
        existing_type=sa.Text(),
        nullable=False,
    )

    op.add_column("users", sa.Column("name", sa.Text(), nullable=True))
    op.execute(
        """
        UPDATE users
        SET name = CASE
            WHEN last_name = '' THEN first_name
            ELSE first_name || ' ' || last_name
        END
        """
    )
    op.alter_column("users", "name", existing_type=sa.Text(), nullable=False)
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")

    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute("ALTER TYPE user_role RENAME VALUE 'student' TO 'student_staff'")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role SET DEFAULT 'student_staff'::user_role"
    )
