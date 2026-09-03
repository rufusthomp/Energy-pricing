"""weather observations

Hourly reanalysis weather at a handful of points chosen to represent where GB wind and
solar output and demand actually come from.

Stored long, one row per (time, location, variable), for the same reason `commodity_price`
is: every series is kept as observed and separate from every other, so how they are
combined into a national wind proxy stays a modelling choice made in the query rather
than baked into the data. Adding a variable then becomes a data change, not a schema
change.

A note on what this is and is not. These are *reanalysis* values, the weather that
actually happened, not the forecast an operator would have held the day before. Using
them is mildly optimistic, but only mildly: unlike day-ahead price forecasts, day-ahead
weather forecasts are genuinely accurate at national aggregate. That asymmetry is the
whole reason the ablation is informative about a realistic operator rather than a
hypothetical one.

No foreign key to `settlement_period`, deliberately. Weather is an independent
observation series, and the ETL rebuilds `settlement_period` with RESTART IDENTITY, which
would otherwise cascade this away on every reload of data that is expensive to re-fetch.

Revision ID: a305783f9fcc
Revises: f75c7e384d2f
Create Date: 2026-09-03
"""

from alembic import op

revision = "a305783f9fcc"
down_revision = "f75c7e384d2f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Dimension: which points stand in for GB. Hand-curated, so it sits alongside `fuel`
    # as a modelling layer rather than an observed fact.
    op.execute("""
        CREATE TABLE weather_location (
            location    TEXT PRIMARY KEY,
            latitude    DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
            longitude   DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
            description TEXT NOT NULL
        )
    """)

    op.execute("""
        INSERT INTO weather_location (location, latitude, longitude, description) VALUES
        ('scotland',   57.00, -4.00, 'Highland onshore wind, the largest GB wind region'),
        ('north_sea',  54.50,  2.00, 'Dogger Bank area, the offshore wind cluster'),
        ('irish_sea',  53.80, -3.50, 'North west offshore wind'),
        ('south',      51.00, -1.00, 'Southern England, where most GB solar sits'),
        ('london',     51.50, -0.13, 'Demand centre, for the temperature-driven load signal')
    """)

    # One row per time, place and variable. Units travel with the value because they
    # differ by variable: never compare across variables without reading it.
    op.execute("""
        CREATE TABLE weather (
            datetime TIMESTAMP NOT NULL,
            location TEXT NOT NULL REFERENCES weather_location(location),
            variable TEXT NOT NULL,  -- 'wind_speed_100m' | 'shortwave_radiation' | 'temperature_2m'
            value    DOUBLE PRECISION NOT NULL,
            unit     TEXT NOT NULL,  -- 'km/h' | 'W/m2' | 'degC'
            PRIMARY KEY (datetime, location, variable)
        )
    """)
    # Joining to the settlement calendar is the common access path, and the composite
    # primary key is already leftmost on datetime, so no extra index is needed for it.
    op.execute("CREATE INDEX idx_weather_variable ON weather(variable, datetime)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS weather")
    op.execute("DROP TABLE IF EXISTS weather_location")
