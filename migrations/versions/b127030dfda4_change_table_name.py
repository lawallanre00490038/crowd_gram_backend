"""Rename projectallocation to agentallocation"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'b127030dfda4'
down_revision = '16efaa9c7542'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Rename the table instead of dropping it."""
    op.rename_table('projectallocation', 'agentallocation')


def downgrade() -> None:
    """Revert the rename if you downgrade."""
    op.rename_table('agentallocation', 'projectallocation')
