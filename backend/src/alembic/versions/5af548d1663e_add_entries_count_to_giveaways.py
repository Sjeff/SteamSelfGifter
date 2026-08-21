"""add entries count to giveaways

Revision ID: 5af548d1663e
Revises: 02befc4dfd90
Create Date: 2026-08-21 13:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5af548d1663e'
down_revision: Union[str, Sequence[str], None] = '02befc4dfd90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('giveaways', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'entries',
                sa.Integer(),
                nullable=False,
                server_default='0',
                comment='Entry count as of the last scan (0 = none yet or unknown)',
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('giveaways', schema=None) as batch_op:
        batch_op.drop_column('entries')
