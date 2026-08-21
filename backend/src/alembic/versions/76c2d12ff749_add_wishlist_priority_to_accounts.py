"""add wishlist_priority to accounts

Revision ID: 76c2d12ff749
Revises: b2c3d4e5f6a7
Create Date: 2026-08-21 13:21:45.134034

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76c2d12ff749'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('accounts', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'wishlist_priority',
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
                comment='Process wishlist giveaways before general autojoin, bypassing price/game-quality filters',
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('accounts', schema=None) as batch_op:
        batch_op.drop_column('wishlist_priority')
