"""baselines_scans_incidents

Revision ID: 8c3d7f1b2e4a
Revises: 04b6dd555033
Create Date: 2026-10-12 01:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c3d7f1b2e4a'
down_revision: Union[str, Sequence[str], None] = '04b6dd555033'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema for persistent baselines, scan runs, and incident lifecycle."""
    # 1. Create project_baselines table
    op.create_table(
        'project_baselines',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('version_tag', sa.String(length=100), nullable=True),
        sa.Column('contracts', sa.JSON(), nullable=False),
        sa.Column('inventory', sa.JSON(), nullable=False),
        sa.Column('source_scan_id', sa.String(length=36), nullable=True),
        sa.Column('content_hash', sa.String(length=128), nullable=True),
        sa.Column('created_by', sa.String(length=36), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_promoted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('promoted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('promoted_by', sa.String(length=36), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_scan_id'], ['scan_runs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'version_number', name='uq_project_baseline_version')
    )
    with op.batch_alter_table('project_baselines', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_project_baselines_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_project_baselines_is_active'), ['is_active'], unique=False)

    # 2. Create incident_events table
    op.create_table(
        'incident_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('incident_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('actor_id', sa.String(length=36), nullable=True),
        sa.Column('from_status', sa.String(length=50), nullable=True),
        sa.Column('to_status', sa.String(length=50), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('incident_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_incident_events_incident_id'), ['incident_id'], unique=False)

    # 3. Add scan_runs columns
    with op.batch_alter_table('scan_runs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('detection_mode', sa.String(length=50), nullable=True, server_default='algorithmic'))
        batch_op.add_column(sa.Column('capabilities_executed', sa.JSON(), nullable=False, server_default='[]'))
        batch_op.add_column(sa.Column('duration_seconds', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('summary_counts', sa.JSON(), nullable=False, server_default='{}'))
        batch_op.add_column(sa.Column('findings_json', sa.JSON(), nullable=False, server_default='[]'))
        batch_op.add_column(sa.Column('is_local', sa.Boolean(), nullable=False, server_default=sa.text('false')))
        batch_op.add_column(sa.Column('sync_status', sa.String(length=50), nullable=False, server_default='synchronized'))
        batch_op.add_column(sa.Column('client_run_id', sa.String(length=100), nullable=True))
        batch_op.create_index(batch_op.f('ix_scan_runs_client_run_id'), ['client_run_id'], unique=False)

    # 4. Add incidents columns
    with op.batch_alter_table('incidents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('provenance', sa.String(length=50), nullable=False, server_default='contract_diff'))
        batch_op.add_column(sa.Column('occurrence_count', sa.Integer(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('recommended_action', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('resolution_notes', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('acknowledged_by', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('reopened_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('last_scan_id', sa.String(length=36), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('incidents', schema=None) as batch_op:
        batch_op.drop_column('last_scan_id')
        batch_op.drop_column('reopened_at')
        batch_op.drop_column('acknowledged_by')
        batch_op.drop_column('acknowledged_at')
        batch_op.drop_column('resolution_notes')
        batch_op.drop_column('recommended_action')
        batch_op.drop_column('occurrence_count')
        batch_op.drop_column('provenance')

    with op.batch_alter_table('scan_runs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_scan_runs_client_run_id'))
        batch_op.drop_column('client_run_id')
        batch_op.drop_column('sync_status')
        batch_op.drop_column('is_local')
        batch_op.drop_column('findings_json')
        batch_op.drop_column('summary_counts')
        batch_op.drop_column('duration_seconds')
        batch_op.drop_column('capabilities_executed')
        batch_op.drop_column('detection_mode')

    with op.batch_alter_table('incident_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_incident_events_incident_id'))
    op.drop_table('incident_events')

    with op.batch_alter_table('project_baselines', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_project_baselines_is_active'))
        batch_op.drop_index(batch_op.f('ix_project_baselines_project_id'))
    op.drop_table('project_baselines')
