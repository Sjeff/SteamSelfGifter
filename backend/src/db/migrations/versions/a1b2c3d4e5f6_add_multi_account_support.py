"""Add multi-account support

Revision ID: a1b2c3d4e5f6
Revises: 386598c59e70
Create Date: 2026-03-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '386598c59e70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add multi-account support."""

    # === Step 1: Create accounts table ===
    op.create_table(
        'accounts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False, server_default='Default'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='0'),
        # Credentials
        sa.Column('phpsessid', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=False,
                  server_default='Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:82.0) Gecko/20100101 Firefox/82.0'),
        sa.Column('xsrf_token', sa.String(), nullable=True),
        # DLC
        sa.Column('dlc_enabled', sa.Boolean(), nullable=False, server_default='0'),
        # Safety
        sa.Column('safety_check_enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('auto_hide_unsafe', sa.Boolean(), nullable=False, server_default='1'),
        # Autojoin
        sa.Column('autojoin_enabled', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('autojoin_start_at', sa.Integer(), nullable=False, server_default='350'),
        sa.Column('autojoin_stop_at', sa.Integer(), nullable=False, server_default='200'),
        sa.Column('autojoin_min_price', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('autojoin_min_score', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('autojoin_min_reviews', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('autojoin_max_game_age', sa.Integer(), nullable=True),
        # Scheduler
        sa.Column('scan_interval_minutes', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('max_entries_per_cycle', sa.Integer(), nullable=True),
        sa.Column('automation_enabled', sa.Boolean(), nullable=False, server_default='0'),
        # Advanced
        sa.Column('max_scan_pages', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('entry_delay_min', sa.Integer(), nullable=False, server_default='8'),
        sa.Column('entry_delay_max', sa.Integer(), nullable=False, server_default='12'),
        # Metadata
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # === Step 2: Migrate existing settings to default account ===
    # Copy existing settings (id=1) into the new accounts table
    op.execute("""
        INSERT INTO accounts (
            name, is_active, is_default,
            phpsessid, user_agent, xsrf_token,
            dlc_enabled, safety_check_enabled, auto_hide_unsafe,
            autojoin_enabled, autojoin_start_at, autojoin_stop_at,
            autojoin_min_price, autojoin_min_score, autojoin_min_reviews,
            autojoin_max_game_age, scan_interval_minutes, max_entries_per_cycle,
            automation_enabled, max_scan_pages, entry_delay_min, entry_delay_max,
            last_synced_at, created_at, updated_at
        )
        SELECT
            'Default', 1, 1,
            phpsessid, user_agent, COALESCE(xsrf_token, NULL),
            dlc_enabled, safety_check_enabled, auto_hide_unsafe,
            autojoin_enabled, autojoin_start_at, autojoin_stop_at,
            autojoin_min_price, autojoin_min_score, autojoin_min_reviews,
            autojoin_max_game_age, scan_interval_minutes, max_entries_per_cycle,
            automation_enabled, max_scan_pages, entry_delay_min, entry_delay_max,
            last_synced_at, created_at, updated_at
        FROM settings
        WHERE id = 1
    """)

    # Fallback: if settings table was empty (fresh install), create a blank default account
    op.execute("""
        INSERT INTO accounts (name, is_active, is_default, user_agent, created_at, updated_at)
        SELECT 'Default', 1, 1,
               'Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:82.0) Gecko/20100101 Firefox/82.0',
               CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE is_default = 1)
    """)

    # === Step 3: Add account_id to giveaways (nullable first) ===
    with op.batch_alter_table('giveaways', schema=None) as batch_op:
        batch_op.add_column(sa.Column('account_id', sa.Integer(), nullable=True))
        # Remove old unique constraint on code alone
        batch_op.drop_index('ix_giveaways_code')

    # === Step 4: Backfill giveaways with default account_id ===
    op.execute("""
        UPDATE giveaways
        SET account_id = (SELECT id FROM accounts WHERE is_default = 1 LIMIT 1)
        WHERE account_id IS NULL
    """)

    # === Step 5: Add FK, composite unique index, make account_id NOT NULL on giveaways ===
    with op.batch_alter_table('giveaways', schema=None) as batch_op:
        batch_op.alter_column('account_id', nullable=False)
        batch_op.create_foreign_key(
            'fk_giveaways_account_id', 'accounts', ['account_id'], ['id']
        )
        batch_op.create_index('ix_giveaways_account_id', ['account_id'], unique=False)
        # New composite unique: code + account_id (two accounts can find same giveaway)
        batch_op.create_index(
            'ix_giveaways_code_account', ['code', 'account_id'], unique=True
        )
        # Keep a non-unique index on code alone for single-code lookups
        batch_op.create_index('ix_giveaways_code', ['code'], unique=False)

    # === Step 6: Add account_id to activity_logs ===
    with op.batch_alter_table('activity_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('account_id', sa.Integer(), nullable=True))

    op.execute("""
        UPDATE activity_logs
        SET account_id = (SELECT id FROM accounts WHERE is_default = 1 LIMIT 1)
        WHERE account_id IS NULL
    """)

    with op.batch_alter_table('activity_logs', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_activity_logs_account_id', 'accounts', ['account_id'], ['id']
        )
        batch_op.create_index('ix_activity_logs_account_id', ['account_id'], unique=False)

    # === Step 7: Add account_id to scheduler_state ===
    # First check if scheduler_state has an existing row with id=1 and migrate it
    with op.batch_alter_table('scheduler_state', schema=None) as batch_op:
        batch_op.add_column(sa.Column('account_id', sa.Integer(), nullable=True))

    op.execute("""
        UPDATE scheduler_state
        SET account_id = (SELECT id FROM accounts WHERE is_default = 1 LIMIT 1)
        WHERE account_id IS NULL
    """)

    with op.batch_alter_table('scheduler_state', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_scheduler_state_account_id', 'accounts', ['account_id'], ['id']
        )
        batch_op.create_index(
            'ix_scheduler_state_account_id', ['account_id'], unique=True
        )

    # Also change scheduler_state id to autoincrement (remove fixed id=1 constraint)
    # SQLite doesn't allow changing PK type, so we leave id as-is but it's fine
    # The new unique constraint on account_id ensures one row per account

    # === Step 8: Add account_id to entries ===
    with op.batch_alter_table('entries', schema=None) as batch_op:
        batch_op.add_column(sa.Column('account_id', sa.Integer(), nullable=True))

    op.execute("""
        UPDATE entries
        SET account_id = (SELECT id FROM accounts WHERE is_default = 1 LIMIT 1)
        WHERE account_id IS NULL
    """)

    with op.batch_alter_table('entries', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_entries_account_id', 'accounts', ['account_id'], ['id']
        )
        batch_op.create_index('ix_entries_account_id', ['account_id'], unique=False)


def downgrade() -> None:
    """Remove multi-account support."""

    # Remove account_id from entries
    with op.batch_alter_table('entries', schema=None) as batch_op:
        batch_op.drop_index('ix_entries_account_id')
        batch_op.drop_constraint('fk_entries_account_id', type_='foreignkey')
        batch_op.drop_column('account_id')

    # Remove account_id from scheduler_state
    with op.batch_alter_table('scheduler_state', schema=None) as batch_op:
        batch_op.drop_index('ix_scheduler_state_account_id')
        batch_op.drop_constraint('fk_scheduler_state_account_id', type_='foreignkey')
        batch_op.drop_column('account_id')

    # Remove account_id from activity_logs
    with op.batch_alter_table('activity_logs', schema=None) as batch_op:
        batch_op.drop_index('ix_activity_logs_account_id')
        batch_op.drop_constraint('fk_activity_logs_account_id', type_='foreignkey')
        batch_op.drop_column('account_id')

    # Restore giveaways.code to globally unique
    with op.batch_alter_table('giveaways', schema=None) as batch_op:
        batch_op.drop_index('ix_giveaways_code_account')
        batch_op.drop_index('ix_giveaways_code')
        batch_op.drop_index('ix_giveaways_account_id')
        batch_op.drop_constraint('fk_giveaways_account_id', type_='foreignkey')
        batch_op.drop_column('account_id')
        batch_op.create_index('ix_giveaways_code', ['code'], unique=True)

    op.drop_table('accounts')
