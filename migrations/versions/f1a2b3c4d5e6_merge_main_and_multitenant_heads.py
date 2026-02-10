"""Merge main and multi-tenant heads

This resolves multiple Alembic heads by merging:
- 9f3c2d1a4b67 (add_visit_id_to_prescriptions)
- 30cccf5b0ba5 (add_password_reset_token_fields)

Revision ID: f1a2b3c4d5e6
Revises: 9f3c2d1a4b67, 30cccf5b0ba5
Create Date: 2026-02-10 07:10:00.000000
"""

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


# revision identifiers, used by Alembic.
revision = "f1a2b3c4d5e6"
down_revision = ("9f3c2d1a4b67", "30cccf5b0ba5")
branch_labels = None
depends_on = None


def upgrade():
    """No-op merge migration."""
    pass


def downgrade():
    """No-op merge migration."""
    pass

