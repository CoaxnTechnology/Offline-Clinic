"""Add visits table for Visit/Order model

Revision ID: a1b2c3d4e5f6
Revises: 72409bc776e5
Create Date: 2026-02-09 12:45:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '72409bc776e5'
branch_labels = None
depends_on = None


def upgrade():
    """Create visits table matching Visit model."""
    op.create_table(
        'visits',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('clinic_id', sa.Integer(), sa.ForeignKey('clinics.id'), nullable=True, index=True),
        sa.Column('appointment_id', sa.Integer(), sa.ForeignKey('appointments.id'), nullable=False),
        sa.Column('patient_id', sa.String(length=20), sa.ForeignKey('patients.id'), nullable=False),
        sa.Column('accession_number', sa.String(length=64), nullable=True),
        sa.Column('visit_date', sa.Date(), nullable=False),
        sa.Column('visit_status', sa.String(length=30), nullable=False, server_default='scheduled'),
        sa.Column('exam_type', sa.String(length=100), nullable=True),
        sa.Column('modality', sa.String(length=10), nullable=False, server_default='US'),
        sa.Column('requested_procedure_id', sa.String(length=64), nullable=True),
        sa.Column('scheduled_procedure_step_id', sa.String(length=64), nullable=True),
        sa.Column('study_instance_uid', sa.String(length=255), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('admins.id'), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Indexes and constraints (idempotent: only create if not already present)
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'visits'
    """))
    existing_indexes = {row[0] for row in result.fetchall()}

    with op.batch_alter_table('visits', schema=None) as batch_op:
        if 'ix_visits_clinic_id' not in existing_indexes:
            batch_op.create_index(batch_op.f('ix_visits_clinic_id'), ['clinic_id'], unique=False)
        if 'ix_visits_appointment_id' not in existing_indexes:
            batch_op.create_index(batch_op.f('ix_visits_appointment_id'), ['appointment_id'], unique=True)
        if 'ix_visits_patient_id' not in existing_indexes:
            batch_op.create_index(batch_op.f('ix_visits_patient_id'), ['patient_id'], unique=False)
        if 'ix_visits_accession_number' not in existing_indexes:
            batch_op.create_index(batch_op.f('ix_visits_accession_number'), ['accession_number'], unique=True)
        if 'ix_visits_visit_date' not in existing_indexes:
            batch_op.create_index(batch_op.f('ix_visits_visit_date'), ['visit_date'], unique=False)
        if 'ix_visits_visit_status' not in existing_indexes:
            batch_op.create_index(batch_op.f('ix_visits_visit_status'), ['visit_status'], unique=False)
        if 'ix_visits_requested_procedure_id' not in existing_indexes:
            batch_op.create_index(batch_op.f('ix_visits_requested_procedure_id'), ['requested_procedure_id'], unique=False)
        if 'ix_visits_scheduled_procedure_step_id' not in existing_indexes:
            batch_op.create_index(batch_op.f('ix_visits_scheduled_procedure_step_id'), ['scheduled_procedure_step_id'], unique=False)
        if 'ix_visits_study_instance_uid' not in existing_indexes:
            batch_op.create_index(batch_op.f('ix_visits_study_instance_uid'), ['study_instance_uid'], unique=False)
        if 'ix_visits_created_by' not in existing_indexes:
            batch_op.create_index(batch_op.f('ix_visits_created_by'), ['created_by'], unique=False)
        if 'ix_visits_deleted_at' not in existing_indexes:
            batch_op.create_index(batch_op.f('ix_visits_deleted_at'), ['deleted_at'], unique=False)


def downgrade():
    """Drop visits table."""
    with op.batch_alter_table('visits', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_visits_deleted_at'))
        batch_op.drop_index(batch_op.f('ix_visits_created_by'))
        batch_op.drop_index(batch_op.f('ix_visits_study_instance_uid'))
        batch_op.drop_index(batch_op.f('ix_visits_scheduled_procedure_step_id'))
        batch_op.drop_index(batch_op.f('ix_visits_requested_procedure_id'))
        batch_op.drop_index(batch_op.f('ix_visits_visit_status'))
        batch_op.drop_index(batch_op.f('ix_visits_visit_date'))
        batch_op.drop_index(batch_op.f('ix_visits_accession_number'))
        batch_op.drop_index(batch_op.f('ix_visits_patient_id'))
        batch_op.drop_index(batch_op.f('ix_visits_appointment_id'))
        batch_op.drop_index(batch_op.f('ix_visits_clinic_id'))

    op.drop_table('visits')

