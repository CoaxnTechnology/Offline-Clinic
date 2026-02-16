"""Add dicom_ae_title to Clinic - Fix migration chain

Revision ID: add_dicom_ae_title_v2
Revises: dda99c309d17
Create Date: 2026-02-16 17:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_dicom_ae_title_v2"
down_revision = "dda99c309d17"
branch_labels = None
depends_on = None


def upgrade():
    # Check if columns exist and add only if they don't
    conn = op.get_bind()

    # Check if dicom_measurements.clinic_id exists
    result = conn.execute(
        sa.text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'dicom_measurements' AND column_name = 'clinic_id'
    """)
    )
    if result.fetchone() is None:
        with op.batch_alter_table("dicom_measurements", schema=None) as batch_op:
            batch_op.add_column(sa.Column("clinic_id", sa.Integer(), nullable=True))

    # Check if prescriptions.clinic_id exists
    result = conn.execute(
        sa.text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'prescriptions' AND column_name = 'clinic_id'
    """)
    )
    if result.fetchone() is None:
        with op.batch_alter_table("prescriptions", schema=None) as batch_op:
            batch_op.add_column(sa.Column("clinic_id", sa.Integer(), nullable=True))

    # Add dicom_ae_title to clinics
    result = conn.execute(
        sa.text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'clinics' AND column_name = 'dicom_ae_title'
    """)
    )
    if result.fetchone() is None:
        with op.batch_alter_table("clinics", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("dicom_ae_title", sa.String(length=16), nullable=True)
            )


def downgrade():
    with op.batch_alter_table("clinics", schema=None) as batch_op:
        batch_op.drop_column("dicom_ae_title")
