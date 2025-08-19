"""Initial migration

Revision ID: 0001
Revises: 
Create Date: 2024-12-21 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create credential table
    op.create_table('credential',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('credential_id', sa.String(length=50), nullable=False),
        sa.Column('subject_id', sa.String(length=255), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('format', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('issued', sa.DateTime(), nullable=False),
        sa.Column('expires', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('credential_id')
    )
    op.create_index(op.f('ix_credential_credential_id'), 'credential', ['credential_id'], unique=False)
    
    # Create verification_log table
    op.create_table('verification_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('checked_at', sa.DateTime(), nullable=False),
        sa.Column('credential_id', sa.String(length=50), nullable=False),
        sa.Column('result', sa.String(length=10), nullable=False),
        sa.Column('response_time', sa.Integer(), nullable=False),
        sa.Column('verifier', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['credential_id'], ['credential.credential_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_verification_log_checked_at'), 'verification_log', ['checked_at'], unique=False)
    op.create_index(op.f('ix_verification_log_credential_id'), 'verification_log', ['credential_id'], unique=False)


def downgrade() -> None:
    # Drop verification_log table first (due to foreign key constraint)
    op.drop_index(op.f('ix_verification_log_credential_id'), table_name='verification_log')
    op.drop_index(op.f('ix_verification_log_checked_at'), table_name='verification_log')
    op.drop_table('verification_log')
    
    # Drop credential table
    op.drop_index(op.f('ix_credential_credential_id'), table_name='credential')
    op.drop_table('credential') 