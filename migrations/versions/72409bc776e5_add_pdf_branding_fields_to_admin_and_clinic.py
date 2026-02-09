"""Add PDF branding fields to admin and clinic

Revision ID: 72409bc776e5
Revises: 7ab18ec47311
Create Date: 2026-02-09 12:27:21.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '72409bc776e5'
down_revision = '7ab18ec47311'
branch_labels = None
depends_on = None


def upgrade():
    # Add PDF branding fields to admins table (for physician digital signature)
    with op.batch_alter_table('admins', schema=None) as batch_op:
        batch_op.add_column(sa.Column('signature_image_path', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('license_number', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('qualifications', sa.String(length=255), nullable=True))
    
    # Add PDF branding fields to clinics table (for clinic logo and header/footer)
    with op.batch_alter_table('clinics', schema=None) as batch_op:
        batch_op.add_column(sa.Column('logo_path', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('header_text', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('footer_text', sa.String(length=255), nullable=True))


def downgrade():
    # Remove PDF branding fields from clinics table
    with op.batch_alter_table('clinics', schema=None) as batch_op:
        batch_op.drop_column('footer_text')
        batch_op.drop_column('header_text')
        batch_op.drop_column('logo_path')
    
    # Remove PDF branding fields from admins table
    with op.batch_alter_table('admins', schema=None) as batch_op:
        batch_op.drop_column('qualifications')
        batch_op.drop_column('license_number')
        batch_op.drop_column('signature_image_path')
