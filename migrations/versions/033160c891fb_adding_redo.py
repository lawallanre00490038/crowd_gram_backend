"""adding redo

Revision ID: 033160c891fb
Revises: b0ee234c2697
Create Date: 2025-10-10 15:01:10.410797

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '033160c891fb'
down_revision: Union[str, None] = 'b0ee234c2697'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Add new enum value
    op.execute("ALTER TYPE status ADD VALUE IF NOT EXISTS 'redo';")

def downgrade():
    # Postgres doesn’t allow removing values from ENUM easily
    # So just document it
    pass
