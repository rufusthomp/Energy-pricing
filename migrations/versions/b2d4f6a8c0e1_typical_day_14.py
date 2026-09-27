"""typical day, 14-day window

The pre-registered robustness check "a 14-day TD window", omitted from the first draft
and caught by the referee. Its own strategy so it cannot be confused with the 28-day
operator in model.run.

Revision ID: b2d4f6a8c0e1
Revises: a9c3d5e7f1b2
Create Date: 2026-09-27
"""

from alembic import op

revision = "b2d4f6a8c0e1"
down_revision = "a9c3d5e7f1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO model.strategy (name, description) VALUES
        ('typical_day_14', 'As typical_day, on the mean price by market hour over the previous '
                           '14 days (at least 10 complete). Pre-registered robustness check.')
    """)


def downgrade() -> None:
    op.execute("DELETE FROM model.strategy WHERE name = 'typical_day_14'")
