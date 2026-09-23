"""panel calendar and daily results

Additive only. Three things the panel analysis needs before its first backtest.

## Market timezone on the zone

The coupled European day-ahead auction trades one delivery day, defined on Central
European Time, for every zone in the coupling. Verified against ENTSO-E's own price
documents for 2020-06-10: DE_LU, IE_SEM, PT and FI all publish the day as 22:00Z to
22:00Z, which is 23:00 local in Dublin and Lisbon and 01:00 local in Helsinki. GB, outside
the coupling, publishes 23:00Z to 23:00Z, its own London day.

So a zone has two clocks. `timezone` is its civil time, the one demand follows, and the
right one for hour-of-day and weekend effects. `market_timezone` is the auction's, the one
that defines a delivery day. A battery optimised over "a day" must use the second,
otherwise in three zones the auction's day is split across two of ours.

## entsoe.calendar

Every zone-hour from the first to the last panel price, with both clocks resolved. It
replaces a timezone conversion in every panel query, which is exactly the kind of
repeated, easy-to-get-wrong expression that has already produced one bug in this project.

It is a materialized view, not a table: it is derived, so the no-derived-data rule keeps it
out of the tables, but at 1.6M rows computing it per query would be slow. It is refreshed
by `load_zones` after every load. The grid is complete by construction, so a LEFT JOIN
from it shows gaps rather than hiding them.

## model.daily_result

Backtest output for the panel, one row per run, zone and delivery day, per the storage
decision in docs/data-scaling.md. Per-period dispatch is kept for GB only.

`revenue` is stored here, which the rest of the schema does not do: elsewhere revenue is
a join of dispatch against price and so stays a query. At daily grain there is no stored
dispatch to join, so it cannot be recomputed, and recomputing it means re-solving the
optimisation. It is in the zone's price currency. Cycle counts are not stored, because
they are discharged energy over capacity, which the query can compute.

Revision ID: f7a1b4c5d6e8
Revises: e6f0a3b4c5d7
Create Date: 2026-09-23
"""

from alembic import op

revision = "f7a1b4c5d6e8"
down_revision = "e6f0a3b4c5d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Default is the coupling's clock, because any zone added to this panel is almost
    # certainly a coupled one. Europe/Brussels stands for CET/CEST.
    op.execute("""
        ALTER TABLE ref.zone
            ADD COLUMN market_timezone TEXT NOT NULL DEFAULT 'Europe/Brussels'
    """)
    op.execute("UPDATE ref.zone SET market_timezone = 'Europe/London' WHERE code = 'GB'")

    op.execute("""
        CREATE MATERIALIZED VIEW entsoe.calendar AS
        WITH bounds AS (
            SELECT min(datetime) AS first, max(datetime) AS last FROM entsoe.price
        ),
        hours AS (
            SELECT generate_series(first, last, INTERVAL '1 hour') AS datetime FROM bounds
        ),
        resolved AS (
            SELECT z.zone_id, h.datetime,
                   (h.datetime AT TIME ZONE 'UTC') AT TIME ZONE z.timezone        AS local_datetime,
                   (h.datetime AT TIME ZONE 'UTC') AT TIME ZONE z.market_timezone AS market_datetime
            FROM ref.zone z CROSS JOIN hours h
        )
        SELECT zone_id,
               datetime,
               local_datetime,
               local_datetime::date                        AS local_date,
               EXTRACT(HOUR FROM local_datetime)::smallint  AS local_hour,
               EXTRACT(ISODOW FROM local_datetime)::smallint AS day_of_week,  -- 1 = Monday
               EXTRACT(ISODOW FROM local_datetime) >= 6     AS is_weekend,
               EXTRACT(MONTH FROM local_datetime)::smallint AS month,
               EXTRACT(YEAR FROM local_datetime)::smallint  AS year,
               market_datetime::date                        AS delivery_date
        FROM resolved
    """)
    # Unique, so the view can be refreshed CONCURRENTLY without blocking readers
    op.execute("CREATE UNIQUE INDEX calendar_pkey ON entsoe.calendar(zone_id, datetime)")
    op.execute("CREATE INDEX idx_calendar_delivery ON entsoe.calendar(zone_id, delivery_date)")

    op.execute("""
        CREATE TABLE model.daily_result (
            run_id         INTEGER NOT NULL REFERENCES model.run(run_id) ON DELETE CASCADE,
            zone_id        SMALLINT NOT NULL REFERENCES ref.zone(zone_id),
            delivery_date  DATE NOT NULL,
            revenue        DOUBLE PRECISION NOT NULL,   -- in the zone's price currency
            charged_mwh    DOUBLE PRECISION NOT NULL CHECK (charged_mwh >= 0),
            discharged_mwh DOUBLE PRECISION NOT NULL CHECK (discharged_mwh >= 0),
            min_soc_mwh    DOUBLE PRECISION NOT NULL CHECK (min_soc_mwh >= 0),
            max_soc_mwh    DOUBLE PRECISION NOT NULL,
            PRIMARY KEY (run_id, zone_id, delivery_date),
            CHECK (max_soc_mwh >= min_soc_mwh)
        )
    """)
    op.execute("CREATE INDEX idx_daily_result_zone_date ON model.daily_result(zone_id, delivery_date)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS model.daily_result")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS entsoe.calendar")
    op.execute("ALTER TABLE ref.zone DROP COLUMN IF EXISTS market_timezone")
