"""Add dicom_ae_title to Clinic

Revision ID: add_dicom_ae_title_to_clinic
Revises: f78e091dd096_fix
Create Date: 2026-02-16 17:20:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_dicom_ae_title_to_clinic"
down_revision = "f78e091dd096_fix"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("clinics", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("dicom_ae_title", sa.String(length=16), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("clinics", schema=None) as batch_op:
        batch_op.drop_column("dicom_ae_title")
