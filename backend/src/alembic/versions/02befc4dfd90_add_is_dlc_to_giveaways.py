"""add is_dlc to giveaways

Revision ID: 02befc4dfd90
Revises: 76c2d12ff749
Create Date: 2026-08-21 13:37:06.273358

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '02befc4dfd90'
down_revision: Union[str, Sequence[str], None] = '76c2d12ff749'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('giveaways', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'is_dlc',
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
                comment='Giveaway is for DLC content, not a base game',
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('giveaways', schema=None) as batch_op:
        batch_op.drop_column('is_dlc')
