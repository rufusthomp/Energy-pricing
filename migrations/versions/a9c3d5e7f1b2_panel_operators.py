"""panel operators

Three strategies for the wind/solar composition study (docs/preregistration.md). Each is
the same MILP as the perfect-foresight ceiling, optimised on a different information set
and settled at actual prices, so the gap between any two is purely a difference in
information.

Revision ID: a9c3d5e7f1b2
Revises: f7a1b4c5d6e8
Create Date: 2026-09-27
"""

from alembic import op

revision = "a9c3d5e7f1b2"
down_revision = "f7a1b4c5d6e8"
branch_labels = None
depends_on = None

NAMES = ("typical_day", "persistence", "gbm_forecast")


def upgrade() -> None:
    op.execute("""
        INSERT INTO model.strategy (name, description) VALUES
        ('typical_day',  'MILP on the mean price by market hour over the previous 28 days. '
                         'Knows the calendar shape, nothing about the specific day.'),
        ('persistence',  'MILP on the previous day''s prices, mapped by market hour.'),
        ('gbm_forecast', 'MILP on a gradient-boosted day-ahead price forecast built from '
                         'lagged prices and TSO day-ahead load, wind and solar forecasts.')
    """)


def downgrade() -> None:
    op.execute("DELETE FROM model.strategy WHERE name IN ('typical_day', 'persistence', 'gbm_forecast')")
