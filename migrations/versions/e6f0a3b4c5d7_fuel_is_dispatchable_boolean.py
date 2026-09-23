"""fuel.is_dispatchable as boolean

Deferred from the Postgres migration on purpose: changing how a value is represented
during that migration would have made its byte-for-byte equivalence check meaningless.
It is done here as its own step for the same reason, after the re-keying has been
verified separately.

Revision ID: e6f0a3b4c5d7
Revises: d5e9f2a3b4c6
Create Date: 2026-09-23
"""

from alembic import op

revision = "e6f0a3b4c5d7"
down_revision = "d5e9f2a3b4c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Anything other than 0 or 1 would mean the column held more than a flag, and a
    # silent `<> 0` cast would hide that. Fail instead.
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM ref.fuel WHERE is_dispatchable NOT IN (0, 1)) THEN
                RAISE EXCEPTION 'ref.fuel.is_dispatchable holds values other than 0 and 1';
            END IF;
        END $$
    """)
    op.execute("""
        ALTER TABLE ref.fuel
            ALTER COLUMN is_dispatchable TYPE BOOLEAN USING is_dispatchable = 1
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE ref.fuel
            ALTER COLUMN is_dispatchable TYPE INTEGER USING is_dispatchable::int
    """)
