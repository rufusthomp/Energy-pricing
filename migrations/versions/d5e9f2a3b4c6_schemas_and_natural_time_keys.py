"""schemas and natural time keys

Two structural changes, both content-preserving: every row that existed before exists
after, with the same values. Verified by fingerprinting every table and every query in
sql/queries.sql before and after, in natural-key terms.

## Namespaces instead of prefixes

The database now holds several sources and a modelling layer, and the table names had
started to encode which was which (`zone_price` beside `price`). Postgres schemas do that
job properly:

    ref     hand-curated modelling choices: zone, fuel, weather_location
    gb      GB-only observed series from NESO and Elexon, half-hourly
    entsoe  the European bidding-zone panel, hourly
    model   battery specs, strategies, runs and everything a run produces

So `gb.price` and `entsoe.price` are both simply "price", and the schema says whose. Code
always qualifies names. `search_path` is deliberately left alone: with a `price` in two
schemas, an unqualified name would silently resolve to whichever came first.

## One time key everywhere: a UTC timestamp

The GB tables keyed on `time_id`, a surrogate integer into `settlement_period`. That was
justified in the SQLite build, where timestamps were stored as text and slow to join. In
Postgres a TIMESTAMP is a native 8-byte type that indexes and joins like an integer, so
the justification went with the migration, and what was left was the cost:

- `time_id` was reassigned on every GB rebuild (RESTART IDENTITY), which is why a routine
  reload had to destroy every backtest: dispatch rows would otherwise have pointed at the
  wrong periods.
- GB and the panel could not be joined without going through `settlement_period`.
- `weather`, the newest GB table, had already been keyed on `datetime`, so the GB side
  used both conventions.

Every table now keys on `datetime` (naive UTC), plus `zone_id` where it covers more than
one area. `gb.settlement_period` stays as the GB calendar, keyed on the same timestamp.

## Model outputs no longer depend on the GB load

`model.dispatch` references `model.run` and `ref.zone` but no longer `gb.settlement_period`.
The timestamps it holds are stable across rebuilds now, so a GB reload does not invalidate
them, and the ETL no longer truncates model tables at all. Whether a run's timestamps fall
inside its own window is still checked, by `arbitrage.validate`, after every write.

`dispatch` also gains `zone_id` so every model output shares one key shape. `forecast` is
replaced by `model.price_forecast`, keyed on zone and two timestamps; its `horizon_step`
column is dropped because it is target minus origin, which is derived. The old table was
empty, which the migration asserts before dropping it.

Irreversible: the backup taken before running it is the way back, or a rebuild from the
raw caches.

Revision ID: d5e9f2a3b4c6
Revises: c4d8e1f7a2b3
Create Date: 2026-09-23
"""

from alembic import op

revision = "d5e9f2a3b4c6"
down_revision = "c4d8e1f7a2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for schema in ("ref", "gb", "entsoe", "model"):
        op.execute(f"CREATE SCHEMA {schema}")

    # --- ref: modelling choices -------------------------------------------------------
    for table in ("fuel", "weather_location", "zone"):
        op.execute(f"ALTER TABLE public.{table} SET SCHEMA ref")

    # GB is an area in its own right, and model outputs now carry zone_id, so its row must
    # exist whether or not the panel has ever been loaded. load_zones refreshes it.
    op.execute("""
        INSERT INTO ref.zone (zone_id, code, country_code, name, timezone, currency, rationale)
        VALUES (1, 'GB', 'GB', 'Great Britain', 'Europe/London', 'GBP',
                'Cross-pipeline consistency check against the Elexon MID series')
        ON CONFLICT (code) DO NOTHING
    """)

    # --- model: specs, strategies, runs ------------------------------------------------
    for table in ("battery_spec", "strategy", "model_run"):
        op.execute(f"ALTER TABLE public.{table} SET SCHEMA model")
    op.execute("ALTER TABLE model.model_run RENAME TO run")
    op.execute("ALTER INDEX model.model_run_pkey RENAME TO run_pkey")
    op.execute("ALTER INDEX model.idx_model_run_strategy_battery RENAME TO idx_run_strategy_battery")

    # Which price series a run was scored against. Every existing run used the Elexon MID.
    op.execute("""
        ALTER TABLE model.run ADD COLUMN price_source TEXT NOT NULL DEFAULT 'gb_mid'
            CHECK (price_source IN ('gb_mid', 'entsoe_day_ahead'))
    """)
    op.execute("ALTER TABLE model.run ALTER COLUMN price_source DROP DEFAULT")

    # --- gb: sources that key on datetime already, moved as they are -------------------
    for table in ("commodity_price", "weather"):
        op.execute(f"ALTER TABLE public.{table} SET SCHEMA gb")

    # --- re-key the time_id tables ------------------------------------------------------
    # Rebuilt with CREATE TABLE AS rather than ADD COLUMN + UPDATE: an UPDATE of 3.4M rows
    # leaves a dead copy of every one of them, doubling the table until a VACUUM FULL that
    # cannot run inside this transaction.
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM public.forecast) THEN
                RAISE EXCEPTION 'public.forecast is not empty; its rows would be lost';
            END IF;
        END $$
    """)

    op.execute("""
        CREATE TABLE gb.generation AS
        SELECT sp.datetime, g.fuel_id, g.mw
        FROM public.generation g JOIN public.settlement_period sp USING (time_id)
    """)
    op.execute("""
        CREATE TABLE gb.demand AS
        SELECT sp.datetime, d.nd, d.tsd
        FROM public.demand d JOIN public.settlement_period sp USING (time_id)
    """)
    op.execute("""
        CREATE TABLE gb.price AS
        SELECT sp.datetime, p.price
        FROM public.price p JOIN public.settlement_period sp USING (time_id)
    """)
    op.execute("""
        CREATE TABLE model.dispatch AS
        SELECT d.run_id, (SELECT zone_id FROM ref.zone WHERE code = 'GB') AS zone_id,
               sp.datetime, d.charge_mw, d.discharge_mw, d.soc_mwh
        FROM public.dispatch d JOIN public.settlement_period sp USING (time_id)
    """)

    for table in ("forecast", "dispatch", "generation", "demand", "price"):
        op.execute(f"DROP TABLE public.{table}")

    op.execute("ALTER TABLE public.settlement_period DROP CONSTRAINT settlement_period_pkey")
    op.execute("ALTER TABLE public.settlement_period DROP COLUMN time_id")
    op.execute("ALTER TABLE public.settlement_period DROP CONSTRAINT settlement_period_datetime_key")
    op.execute("ALTER TABLE public.settlement_period ADD PRIMARY KEY (datetime)")
    op.execute("ALTER TABLE public.settlement_period SET SCHEMA gb")

    # CREATE TABLE AS copies types but not constraints, so they are all restated here
    op.execute("""
        ALTER TABLE gb.generation
            ALTER COLUMN datetime SET NOT NULL,
            ALTER COLUMN fuel_id  SET NOT NULL,
            ALTER COLUMN mw       SET NOT NULL,
            ADD PRIMARY KEY (datetime, fuel_id),
            ADD FOREIGN KEY (datetime) REFERENCES gb.settlement_period(datetime),
            ADD FOREIGN KEY (fuel_id)  REFERENCES ref.fuel(fuel_id)
    """)
    # Leftmost-prefix convention: the primary key serves time slices, this serves fuel ones
    op.execute("CREATE INDEX idx_generation_fuel_id ON gb.generation(fuel_id)")

    op.execute("""
        ALTER TABLE gb.demand
            ALTER COLUMN datetime SET NOT NULL,
            ALTER COLUMN nd       SET NOT NULL,
            ALTER COLUMN tsd      SET NOT NULL,
            ADD PRIMARY KEY (datetime),
            ADD FOREIGN KEY (datetime) REFERENCES gb.settlement_period(datetime)
    """)
    op.execute("""
        ALTER TABLE gb.price
            ALTER COLUMN datetime SET NOT NULL,
            ALTER COLUMN price    SET NOT NULL,
            ADD PRIMARY KEY (datetime),
            ADD FOREIGN KEY (datetime) REFERENCES gb.settlement_period(datetime)
    """)

    op.execute("""
        ALTER TABLE model.dispatch
            ALTER COLUMN run_id       SET NOT NULL,
            ALTER COLUMN zone_id      SET NOT NULL,
            ALTER COLUMN datetime     SET NOT NULL,
            ALTER COLUMN charge_mw    SET NOT NULL,
            ALTER COLUMN discharge_mw SET NOT NULL,
            ALTER COLUMN soc_mwh      SET NOT NULL,
            ADD PRIMARY KEY (run_id, zone_id, datetime),
            ADD FOREIGN KEY (run_id)  REFERENCES model.run(run_id) ON DELETE CASCADE,
            ADD FOREIGN KEY (zone_id) REFERENCES ref.zone(zone_id),
            ADD CHECK (charge_mw >= 0),
            ADD CHECK (discharge_mw >= 0),
            ADD CHECK (soc_mwh >= 0),
            ADD CONSTRAINT not_both_directions CHECK (charge_mw = 0 OR discharge_mw = 0)
    """)
    op.execute("CREATE INDEX idx_dispatch_zone_datetime ON model.dispatch(zone_id, datetime)")

    # A price forecast is made at one instant for another, for one zone, by one run. The
    # horizon is target minus origin, so it is computed rather than stored.
    op.execute("""
        CREATE TABLE model.price_forecast (
            run_id          INTEGER NOT NULL REFERENCES model.run(run_id) ON DELETE CASCADE,
            zone_id         SMALLINT NOT NULL REFERENCES ref.zone(zone_id),
            origin          TIMESTAMP NOT NULL,  -- when the forecast was made
            target          TIMESTAMP NOT NULL,  -- the hour or period it is for
            predicted_price DOUBLE PRECISION NOT NULL,
            PRIMARY KEY (run_id, zone_id, origin, target),
            CHECK (target > origin)
        )
    """)
    op.execute("CREATE INDEX idx_price_forecast_target ON model.price_forecast(zone_id, target)")

    # --- entsoe: the panel, prefixes dropped now the schema carries them ---------------
    for old, new in [("zone_price", "price"), ("zone_load", "load"),
                     ("zone_generation", "generation"), ("zone_load_forecast", "load_forecast"),
                     ("zone_vre_forecast", "vre_forecast"), ("zone_capacity", "capacity"),
                     ("zone_ingest", "ingest")]:
        op.execute(f"ALTER TABLE public.{old} SET SCHEMA entsoe")
        op.execute(f"ALTER TABLE entsoe.{old} RENAME TO {new}")
        op.execute(f"ALTER INDEX entsoe.{old}_pkey RENAME TO {new}_pkey")
    for name in ("price", "load", "generation", "load_forecast", "vre_forecast"):
        op.execute(f"ALTER INDEX entsoe.idx_zone_{name}_datetime RENAME TO idx_{name}_datetime")


def downgrade() -> None:
    raise NotImplementedError(
        "d5e9f2a3b4c6 re-keys every GB table and cannot be reversed in place. Restore the "
        "pg_dump taken before upgrading, or rebuild from the raw caches at c4d8e1f7a2b3."
    )
