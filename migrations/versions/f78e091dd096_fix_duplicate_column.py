"""Add clinic_id to DicomMeasurement and Prescription - Fix duplicate column

Revision ID: f78e091dd096_fix
Revises: f78e091dd096
Create Date: 2026-02-16 17:15:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f78e091dd096_fix"
down_revision = "f78e091dd096"
branch_labels = None
depends_on = None


def upgrade():
    # Column already exists in previous migration - this is a no-op fix
    # The original migration failed because column already existed
    pass


def downgrade():
    pass
