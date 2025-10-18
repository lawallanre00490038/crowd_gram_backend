"""adjusted

Revision ID: 6d3aa9a575dc
Revises: b127030dfda4
Create Date: 2025-10-18 15:35:35.629635
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '6d3aa9a575dc'
down_revision: Union[str, None] = 'b127030dfda4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema safely by renaming projectallocation → agentallocation."""
    # 1️⃣ Rename the table itself
    op.rename_table('projectallocation', 'agentallocation')

    # 2️⃣ Drop old foreign key constraints referencing projectallocation
    op.drop_constraint('coinpayment_project_allocation_id_fkey', 'coinpayment', type_='foreignkey')
    op.drop_constraint('submission_assignment_id_fkey', 'submission', type_='foreignkey')

    # 3️⃣ Rename columns to match the new foreign key name
    op.alter_column('coinpayment', 'project_allocation_id', new_column_name='agent_allocation_id')

    # 4️⃣ Recreate foreign key constraints to point to the renamed table
    op.create_foreign_key(
        'coinpayment_agent_allocation_id_fkey',
        'coinpayment', 'agentallocation',
        ['agent_allocation_id'], ['id']
    )

    op.create_foreign_key(
        'submission_assignment_id_fkey',
        'submission', 'agentallocation',
        ['assignment_id'], ['id']
    )


def downgrade() -> None:
    """Downgrade schema safely by reverting agentallocation → projectallocation."""
    # Drop new foreign key constraints
    op.drop_constraint('coinpayment_agent_allocation_id_fkey', 'coinpayment', type_='foreignkey')
    op.drop_constraint('submission_assignment_id_fkey', 'submission', type_='foreignkey')

    # Rename columns back
    op.alter_column('coinpayment', 'agent_allocation_id', new_column_name='project_allocation_id')

    # Recreate old foreign key constraints
    op.create_foreign_key(
        'coinpayment_project_allocation_id_fkey',
        'coinpayment', 'projectallocation',
        ['project_allocation_id'], ['id']
    )

    op.create_foreign_key(
        'submission_assignment_id_fkey',
        'submission', 'projectallocation',
        ['assignment_id'], ['id']
    )

    # Rename table back
    op.rename_table('agentallocation', 'projectallocation')
