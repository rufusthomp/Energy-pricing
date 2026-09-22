"""zone forecasts and capacity

Day-ahead TSO forecasts of load, wind and solar, and installed capacity by year.

The forecasts matter for identification rather than accuracy. They define the operator's
information set at the day-ahead auction without leaning on reanalysis weather, which is
the weather that happened, not the weather anyone expected. They also give an exogenous
treatment: a forecast capacity-factor anomaly is weather, and weather is not chosen by
anyone in the market.

Installed capacity is what makes the structural question reachable. The same weather
shock moves prices more in a zone with more turbines, so the interaction between a
capacity-factor anomaly and installed capacity asks how decarbonisation changes the value
of information. The weather supplies the identifying variation.

Stored wide by category for the same reason as `zone_generation`: the unaggregated
responses stay in the cache.

Revision ID: c4d8e1f7a2b3
Revises: b91c4a7d2e05
Create Date: 2026-09-22
"""

from alembic import op

revision = "c4d8e1f7a2b3"
down_revision = "b91c4a7d2e05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE zone_load_forecast (
            zone_id  SMALLINT NOT NULL REFERENCES zone(zone_id),
            datetime TIMESTAMP NOT NULL,
            mw       DOUBLE PRECISION NOT NULL CHECK (mw >= 0),
            PRIMARY KEY (zone_id, datetime)
        )
    """)

    # Only wind and solar: those are the only production types ENTSO-E forecasts day
    # ahead at zone level. NULL means the zone does not publish that forecast.
    op.execute("""
        CREATE TABLE zone_vre_forecast (
            zone_id  SMALLINT NOT NULL REFERENCES zone(zone_id),
            datetime TIMESTAMP NOT NULL,
            wind_mw  DOUBLE PRECISION,
            solar_mw DOUBLE PRECISION,
            PRIMARY KEY (zone_id, datetime)
        )
    """)
    for table in ("zone_load_forecast", "zone_vre_forecast"):
        op.execute(f"CREATE INDEX idx_{table}_datetime ON {table}(datetime)")

    # Keyed on the requested year, not a timestamp. ENTSO-E stamps the value at local
    # midnight on 1 January, which lands on 31 December of the previous year in UTC, so a
    # timestamp key would put every Continental zone's capacity in the wrong year.
    op.execute("""
        CREATE TABLE zone_capacity (
            zone_id    SMALLINT NOT NULL REFERENCES zone(zone_id),
            year       INTEGER NOT NULL,
            wind_mw    DOUBLE PRECISION,
            solar_mw   DOUBLE PRECISION,
            hydro_mw   DOUBLE PRECISION,
            nuclear_mw DOUBLE PRECISION,
            fossil_mw  DOUBLE PRECISION,
            storage_mw DOUBLE PRECISION,
            other_mw   DOUBLE PRECISION,
            PRIMARY KEY (zone_id, year)
        )
    """)

    # An annual snapshot has no publication resolution, so NULL rather than a fake one
    op.execute("ALTER TABLE zone_ingest ALTER COLUMN resolution_minutes DROP NOT NULL")


def downgrade() -> None:
    op.execute("DELETE FROM zone_ingest WHERE resolution_minutes IS NULL")
    op.execute("ALTER TABLE zone_ingest ALTER COLUMN resolution_minutes SET NOT NULL")
    for table in ("zone_capacity", "zone_vre_forecast", "zone_load_forecast"):
        op.execute(f"DROP TABLE IF EXISTS {table}")
