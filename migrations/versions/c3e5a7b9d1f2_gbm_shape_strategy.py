"""gbm shape forecaster

The referee asked for a forecaster tuned to what arbitrage pays for. `gbm_forecast` is
trained on the price's deviation from the typical-day profile, so part of its effort goes
on the day's level, which a battery that starts and ends empty barely trades on.
`gbm_shape` is the same model trained on the within-day shape only: the deviation after
removing each day's mean from both the price and the profile. Its own strategy so the two
forecasters sit side by side in model.run.

Revision ID: c3e5a7b9d1f2
Revises: b2d4f6a8c0e1
Create Date: 2026-09-29
"""

from alembic import op

revision = "c3e5a7b9d1f2"
down_revision = "b2d4f6a8c0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO model.strategy (name, description) VALUES
        ('gbm_shape', 'As gbm_forecast, but trained on the within-day price shape: the '
                      'deviation from the typical-day profile after removing each day''s '
                      'mean from both. Exploratory, added at the referee''s request.')
    """)


def downgrade() -> None:
    op.execute("DELETE FROM model.strategy WHERE name = 'gbm_shape'")
