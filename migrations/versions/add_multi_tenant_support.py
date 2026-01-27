"""Add multi-tenant support with clinics table

Revision ID: mt001
Revises: 
Create Date: 2026-01-27
"""
from alembic import op
import sqlalchemy as sa
from datetime import date, timedelta

# revision identifiers
revision = 'mt001'
down_revision = '0f452f437c97'
branch_labels = None
depends_on = None


def upgrade():
    # Create clinics table
    op.create_table(
        'clinics',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('address', sa.String(255)),
        sa.Column('phone', sa.String(20)),
        sa.Column('email', sa.String(100)),
        sa.Column('license_key', sa.String(50), unique=True, nullable=False),
        sa.Column('license_type', sa.String(20), default='basic'),
        sa.Column('license_expiry', sa.Date(), nullable=False),
        sa.Column('max_doctors', sa.Integer(), default=1),
        sa.Column('max_patients', sa.Integer(), default=500),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now())
    )
    
    # Add clinic_id to patients table
    op.add_column('patients', sa.Column('clinic_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_patients_clinic', 'patients', 'clinics', ['clinic_id'], ['id'])
    
    # Add clinic_id to appointments table
    op.add_column('appointments', sa.Column('clinic_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_appointments_clinic', 'appointments', 'clinics', ['clinic_id'], ['id'])
    
    # Add clinic_id to admins table
    op.add_column('admins', sa.Column('clinic_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_admins_clinic', 'admins', 'clinics', ['clinic_id'], ['id'])
    
    # Add clinic_id to dicom_images table
    op.add_column('dicom_images', sa.Column('clinic_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_dicom_images_clinic', 'dicom_images', 'clinics', ['clinic_id'], ['id'])
    
    # Add clinic_id to reports table
    op.add_column('reports', sa.Column('clinic_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_reports_clinic', 'reports', 'clinics', ['clinic_id'], ['id'])
    
    # Create default clinic for existing data
    op.execute("""
        INSERT INTO clinics (name, license_key, license_type, license_expiry, max_doctors, max_patients, is_active)
        VALUES ('Default Clinic', 'DEFAULT-0001-0001-0001', 'premium', '2030-12-31', 10, 10000, true)
    """)
    
    # Assign existing data to default clinic (clinic_id = 1)
    op.execute("UPDATE patients SET clinic_id = 1 WHERE clinic_id IS NULL")
    op.execute("UPDATE appointments SET clinic_id = 1 WHERE clinic_id IS NULL")
    op.execute("UPDATE admins SET clinic_id = 1 WHERE clinic_id IS NULL")
    op.execute("UPDATE dicom_images SET clinic_id = 1 WHERE clinic_id IS NULL")
    op.execute("UPDATE reports SET clinic_id = 1 WHERE clinic_id IS NULL")


def downgrade():
    # Remove foreign keys
    op.drop_constraint('fk_patients_clinic', 'patients', type_='foreignkey')
    op.drop_constraint('fk_appointments_clinic', 'appointments', type_='foreignkey')
    op.drop_constraint('fk_admins_clinic', 'admins', type_='foreignkey')
    op.drop_constraint('fk_dicom_images_clinic', 'dicom_images', type_='foreignkey')
    op.drop_constraint('fk_reports_clinic', 'reports', type_='foreignkey')
    
    # Remove clinic_id columns
    op.drop_column('patients', 'clinic_id')
    op.drop_column('appointments', 'clinic_id')
    op.drop_column('admins', 'clinic_id')
    op.drop_column('dicom_images', 'clinic_id')
    op.drop_column('reports', 'clinic_id')
    
    # Drop clinics table
    op.drop_table('clinics')
