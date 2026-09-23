"""Rebuild the database from raw sources in one run.

Alembic owns the schema; this module only owns the data. It therefore truncates and
repopulates rather than dropping and recreating, which is what changed when the build
moved off SQLite: a live database accumulating model runs cannot have its tables
dropped underneath it.

The rebuild is disposable and reproducible, and since the move to timestamp keys it
touches only the GB source tables and the fuel layer they reference. Model outputs key on
the same timestamps, which a rebuild no longer reassigns, so backtest runs survive it.

Run as a module so package imports resolve:

    python -m gbmo.ingest.load [--database-url URL]
"""

import argparse
import io

import pandas as pd
from sqlalchemy import create_engine, text

from gbmo import config
from gbmo.ingest import reference, transform, weather

# CPS is synthesised rather than sourced, so it needs an explicit end. It covers every
# month in the modelled span so the query never hits a missing top-up.
CPS_END_YEAR = 2027

PENCE_PER_KWH = "pence_per_kWh_GCV"
GBP_PER_TCO2 = "GBP_per_tCO2"

# Everything this ETL owns: the GB source tables and the fuel layer the generation fact
# references. Facts before the dimensions they reference, though CASCADE makes the order
# cosmetic.
#
# Nothing in `model` is listed, and nothing there references these tables, so CASCADE
# cannot reach it: backtest runs survive a rebuild. They could not before the move to
# timestamp keys, because RESTART IDENTITY reassigned every time_id underneath them.
# ref.zone, ref.weather_location and the model specs are seeded by migration or by the
# panel loader and are never touched here.
TABLES = ("gb.generation", "gb.demand", "gb.price", "gb.commodity_price", "gb.weather",
          "gb.settlement_period", "ref.fuel")


def copy_frame(engine, table, df):
    """Bulk load a frame via COPY.

    `DataFrame.to_sql` issues parameterised INSERTs and is unusable at this scale: the
    generation fact alone is 3.4M rows. COPY streams the whole frame in one statement.

    NULLs travel as empty unquoted fields, which is what COPY's CSV format already
    treats as NULL. That avoids a backslash marker having to survive both Python string
    escaping and Postgres string literal parsing. Safe here because no column carries a
    genuine empty string: `commodity` and `efficiency` are either populated or absent.
    """
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False, na_rep="")
    buf.seek(0)

    columns = ", ".join(df.columns)
    statement = f"COPY {table} ({columns}) FROM STDIN WITH (FORMAT csv)"

    raw = engine.raw_connection()
    try:
        with raw.driver_connection.cursor() as cur, cur.copy(statement) as copy:
            copy.write(buf.read())
        raw.commit()
    finally:
        raw.close()


def truncate_all(engine):
    with engine.begin() as con:
        con.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))


def load_fuel(engine):
    """The hand-curated modelling layer."""
    columns = ["name", "mc", "carbon_factor", "efficiency", "commodity", "is_dispatchable"]
    copy_frame(engine, "ref.fuel", pd.DataFrame(reference.FUELS, columns=columns))


def load_time_and_generation(engine):
    """Wide NESO generation mix -> `gb.settlement_period` calendar + long `gb.generation`.

    Returns the settlement timestamps, which the demand and price loaders filter to: every
    GB fact references the calendar, so a row outside it would fail the foreign key.
    """
    df = pd.read_csv(config.GENERATION_CSV)
    df = df.drop(columns=reference.GENERATION_DERIVED_COLUMNS, axis=1)

    calendar = transform.build_time_dimension(df["DATETIME"])
    copy_frame(engine, "gb.settlement_period", calendar)

    # Wide -> long: one column per fuel becomes one row per (time, fuel)
    df = pd.melt(df, id_vars="DATETIME", var_name="name", value_name="mw")
    df["datetime"] = pd.to_datetime(df["DATETIME"])

    fuel_lookup = pd.read_sql("SELECT fuel_id, name FROM ref.fuel", engine)
    df = df.merge(fuel_lookup, on="name")

    copy_frame(engine, "gb.generation", df[["datetime", "fuel_id", "mw"]])

    return pd.Series(pd.to_datetime(calendar["datetime"]))


def load_demand(engine, settlement_times):
    """18 per-year NESO demand files -> `demand`.

    Settlement date and period are converted to UTC rather than treated as if already
    UTC, because GB settlement periods are defined on the local clock while the
    generation and price feeds are not. See `transform.settlement_period_to_utc`.
    """
    # Sorted so a rebuild is deterministic; glob order is otherwise filesystem-dependent.
    demand_files = sorted(config.DEMAND_DIR.glob(config.DEMAND_GLOB))
    demand_df = pd.concat([pd.read_csv(f) for f in demand_files], ignore_index=True)

    demand_df["datetime"] = transform.settlement_period_to_utc(
        demand_df["SETTLEMENT_DATE"], demand_df["SETTLEMENT_PERIOD"]
    )

    demand_df = demand_df[demand_df["datetime"].isin(settlement_times)]
    demand_df = demand_df[["datetime", "ND", "TSD"]]
    demand_df.columns = demand_df.columns.str.lower()  # Fit naming schema
    # Genuine duplicates only: the clock-change overflow that used to land here is gone
    demand_df = demand_df.drop_duplicates(subset="datetime")

    copy_frame(engine, "gb.demand", demand_df)


def load_price(engine, settlement_times):
    """Cached Elexon MID pull -> `price`, one volume-weighted price per period.

    `startTime` is explicitly UTC (trailing Z, and settlement period 1 on a BST day sits
    at 23:00Z the day before), so dropping the offset yields naive UTC, matching the
    generation feed.
    """
    grouped = transform.collapse_price_providers(pd.read_csv(config.PRICE_CSV))

    grouped["datetime"] = pd.to_datetime(grouped["startTime"], utc=True).dt.tz_localize(None)
    grouped = grouped[grouped["datetime"].isin(settlement_times)]
    grouped = grouped[["datetime", "price"]].drop_duplicates(subset="datetime")

    copy_frame(engine, "gb.price", grouped)


def load_weather(engine):
    """Cached Open-Meteo reanalysis -> `weather`.

    Read from the CSV cache rather than the API: the archive is slow and returns
    intermittent gateway errors, so a rebuild must not depend on it being up. Populate
    the cache with `python -m gbmo.ingest.weather`.
    """
    frame = weather.read_cache(config.FIRST_PRICE_YEAR, config.LAST_YEAR)
    copy_frame(engine, "gb.weather", frame[["datetime", "location", "variable", "value", "unit"]])


def load_commodity(engine):
    """Gas, coal, carbon and FX series -> `commodity_price`.

    Every series is loaded as observed, on a monthly grain, and kept separate from every
    other one. The EUA->UKA splice, whether CPS is added, and QEP vs SAP for gas are all
    modelling choices made at query time, so nothing here is pre-combined. The one
    conversion applied is EUR->GBP on the EUA series, which is a unit change, not a
    modelling choice, and the FX series itself is loaded too so that step stays auditable.
    """
    d = config.COMMODITY_DIR

    gas_qep = transform.quarterly_to_monthly(d / "gas_price_qep_321.csv", "gas_pence_per_kwh_gcv")
    coal_qep = transform.quarterly_to_monthly(d / "coal_price_qep_321.csv", "coal_pence_per_kwh_gcv")
    gas_sap = transform.year_month_to_monthly(d / "gas_sap_monthly_ons.csv", "month", "sap_pence_per_kwh")
    fx = transform.year_month_to_monthly(d / "fx_eur_gbp_monthly_ecb.csv", "month", "gbp_per_eur")
    uka = transform.daily_to_monthly(d / "uka_price_daily_icap.csv", "price_gbp")

    # EUA is quoted in EUR, so it needs the ECB rate before it can sit alongside UKA in GBP
    eua = transform.daily_to_monthly(d / "eua_price_daily_icap.csv", "price_eur")
    eua = eua.merge(fx.rename(columns={"price": "gbp_per_eur"}), on=["year", "month"])
    eua["price"] = eua["price"] * eua["gbp_per_eur"]
    eua = eua[["year", "month", "price"]]

    cps = pd.DataFrame(
        [(y, m) for y in range(config.FIRST_YEAR, CPS_END_YEAR) for m in range(1, 13)],
        columns=["year", "month"],
    )
    cps["price"] = [transform.cps_rate(y, m) for y, m in zip(cps["year"], cps["month"])]

    series = [
        (gas_qep, "gas", "qep", PENCE_PER_KWH),
        (gas_sap, "gas", "sap", PENCE_PER_KWH),
        (coal_qep, "coal", "qep", PENCE_PER_KWH),
        (eua, "carbon", "eua", GBP_PER_TCO2),
        (uka, "carbon", "uka", GBP_PER_TCO2),
        (cps, "carbon", "cps", GBP_PER_TCO2),
        (fx, "fx", "ecb", "GBP_per_EUR"),
    ]

    frames = []
    for frame, commodity, source, unit in series:
        frame = frame.copy()
        frame["commodity"] = commodity
        frame["source"] = source
        frame["unit"] = unit
        frames.append(frame[["year", "month", "commodity", "source", "price", "unit"]])

    copy_frame(engine, "gb.commodity_price", pd.concat(frames, ignore_index=True))


def analyse_all(engine):
    """Refresh planner statistics after the bulk load.

    TRUNCATE followed by COPY leaves pg_stat estimates stale until autovacuum catches
    up, and the planner uses them: on a 3.4M-row fact table that is the difference
    between an index scan and a sequential one. Cheap to do once at the end of a build
    rather than waiting for autovacuum to notice.
    """
    with engine.begin() as con:
        con.execute(text("ANALYZE"))


def build_database(database_url=None):
    """Truncate and repopulate the GB source layer. Returns the URL written to.

    Backtest runs are untouched. There used to be a guard here refusing to rebuild while
    runs existed, because a rebuild reassigned the time_id every dispatch row pointed at.
    Timestamps are not reassigned, so the guard had nothing left to protect.

    One caveat the schema cannot express: a run was scored against the prices as they
    were when it ran. If a rebuild pulls revised source prices, older runs describe the
    old ones. `model.run.created_at` and `git_commit` say when and with what.
    """
    database_url = database_url or config.DATABASE_URL
    engine = create_engine(database_url)

    truncate_all(engine)
    load_fuel(engine)
    settlement_times = load_time_and_generation(engine)
    load_demand(engine, settlement_times)
    load_price(engine, settlement_times)
    load_commodity(engine)
    load_weather(engine)
    analyse_all(engine)

    engine.dispose()
    return database_url


def main():
    parser = argparse.ArgumentParser(description="Rebuild the GB source tables.")
    parser.add_argument("--database-url", default=None, help="Target database URL.")
    args = parser.parse_args()
    print(f"built: {build_database(args.database_url)}")


if __name__ == "__main__":
    main()
