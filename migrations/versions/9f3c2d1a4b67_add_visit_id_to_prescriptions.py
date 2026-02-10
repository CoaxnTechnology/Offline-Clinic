"""Add visit_id to prescriptions

Revision ID: 9f3c2d1a4b67
Revises: 51c270f32e2b
Create Date: 2026-02-10 12:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9f3c2d1a4b67"
# Chain this after the current main head so we don't create a new branch.
# Previous head is 72409bc776e5 -> a1b2c3d4e5f6, so we depend on a1b2c3d4e5f6.
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    """
    Add nullable visit_id column to prescriptions and index it.

    This links each prescription optionally to a Visit (one prescription per visit).
    The migration is written to be idempotent for safety.
    """
    conn = op.get_bind()

    # Check if column already exists (idempotent)
    has_column = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'prescriptions'
              AND column_name = 'visit_id'
            """
        )
    ).scalar()

    if not has_column:
        with op.batch_alter_table("prescriptions", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("visit_id", sa.Integer(), nullable=True)
            )

    # Create index and FK only if they don't already exist
    # Index
    has_index = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM pg_indexes
            WHERE tablename = 'prescriptions'
              AND indexname = 'ix_prescriptions_visit_id'
            """
        )
    ).scalar()

    if not has_index:
        with op.batch_alter_table("prescriptions", schema=None) as batch_op:
            batch_op.create_index(
                "ix_prescriptions_visit_id", ["visit_id"], unique=False
            )

    # Foreign key (best-effort; if it already exists, ignore)
    try:
        with op.batch_alter_table("prescriptions", schema=None) as batch_op:
            batch_op.create_foreign_key(
                "fk_prescriptions_visit_id_visits",
                "visits",
                ["visit_id"],
                ["id"],
            )
    except Exception:
        # If FK already exists or DB doesn't support named FK in this way, ignore
        pass


def downgrade():
    """
    Drop visit_id, its index, and foreign key from prescriptions.
    """
    conn = op.get_bind()

    # Drop FK if it exists
    try:
        with op.batch_alter_table("prescriptions", schema=None) as batch_op:
            batch_op.drop_constraint(
                "fk_prescriptions_visit_id_visits", type_="foreignkey"
            )
    except Exception:
        pass

    # Drop index if it exists
    has_index = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM pg_indexes
            WHERE tablename = 'prescriptions'
              AND indexname = 'ix_prescriptions_visit_id'
            """
        )
    ).scalar()

    if has_index:
        with op.batch_alter_table("prescriptions", schema=None) as batch_op:
            batch_op.drop_index("ix_prescriptions_visit_id")

    # Drop column if it exists
    has_column = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'prescriptions'
              AND column_name = 'visit_id'
            """
        )
    ).scalar()

    if has_column:
        with op.batch_alter_table("prescriptions", schema=None) as batch_op:
            batch_op.drop_column("visit_id")

