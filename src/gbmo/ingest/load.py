"""Rebuild the database from raw sources in one run.

Alembic owns the schema; this module only owns the data. It therefore truncates and
repopulates rather than dropping and recreating, which is what changed when the build
moved off SQLite: a live database accumulating model runs cannot have its tables
dropped underneath it.

The rebuild is still disposable and reproducible. `TRUNCATE ... RESTART IDENTITY`
resets the identity sequences too, so a rebuild assigns the same surrogate keys as the
run before it.

Run as a module so package imports resolve:

    python -m gbmo.ingest.load [--database-url URL]
"""

import argparse
import io

import pandas as pd
from sqlalchemy import create_engine, text

from gbmo import config
from gbmo.ingest import reference, transform

# CPS is synthesised rather than sourced, so it needs an explicit end. It covers every
# month in the modelled span so the query never hits a missing top-up.
CPS_END_YEAR = 2027

PENCE_PER_KWH = "pence_per_kWh_GCV"
GBP_PER_TCO2 = "GBP_per_tCO2"

# Facts before the dimensions they reference, though CASCADE makes the order cosmetic
TABLES = ("generation", "demand", "price", "commodity_price", "settlement_period", "fuel")

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
    copy_frame(engine, "fuel", pd.DataFrame(reference.FUELS, columns=columns))


def load_time_and_generation(engine):
    """Wide NESO generation mix -> `settlement_period` dimension + long `generation` fact.

    Returns the time lookup, which the demand and price loaders both need.
    """
    df = pd.read_csv(config.GENERATION_CSV)
    df = df.drop(columns=reference.GENERATION_DERIVED_COLUMNS, axis=1)

    copy_frame(engine, "settlement_period", transform.build_time_dimension(df["DATETIME"]))

    # Wide -> long: one column per fuel becomes one row per (time, fuel)
    df = pd.melt(df, id_vars="DATETIME", var_name="name", value_name="mw")
    df["DATETIME"] = pd.to_datetime(df["DATETIME"])

    fuel_lookup = pd.read_sql("SELECT fuel_id, name FROM fuel", engine)
    time_lookup = pd.read_sql("SELECT time_id, datetime FROM settlement_period", engine)

    df = df.merge(time_lookup, left_on="DATETIME", right_on="datetime")
    df = df.merge(fuel_lookup, on="name")

    copy_frame(engine, "generation", df[["time_id", "fuel_id", "mw"]])

    return time_lookup


def load_demand(engine, time_lookup):
    """18 per-year NESO demand files -> `demand`.

    KNOWN DEFECT, ported unchanged so the Postgres migration could be verified against
    the SQLite build. GB settlement periods run on the local clock (46 periods on the
    spring change, 50 on the autumn one, max period 50 in this data), but the timestamp
    built below is treated as UTC to match the generation feed. Through BST that
    attaches demand one hour late, and on the long October day periods 47-50 overflow
    into the next day, where drop_duplicates silently discards them. Fixed separately,
    with the before/after measured.
    """
    # Sorted so a rebuild is deterministic; glob order is otherwise filesystem-dependent.
    demand_files = sorted(config.DEMAND_DIR.glob(config.DEMAND_GLOB))
    demand_df = pd.concat([pd.read_csv(f) for f in demand_files], ignore_index=True)

    demand_df["datetime"] = pd.to_datetime(demand_df["SETTLEMENT_DATE"]) + pd.to_timedelta(
        (demand_df["SETTLEMENT_PERIOD"] - 1) * 30, unit="m"
    )

    demand_df = demand_df.merge(time_lookup, on="datetime")
    demand_df = demand_df[["time_id", "ND", "TSD"]]
    demand_df.columns = demand_df.columns.str.lower()  # Fit naming schema
    demand_df = demand_df.drop_duplicates(subset="time_id")

    copy_frame(engine, "demand", demand_df)


def load_price(engine, time_lookup):
    """Cached Elexon MID pull -> `price`, one volume-weighted price per period.

    `startTime` is explicitly UTC (trailing Z, and settlement period 1 on a BST day sits
    at 23:00Z the day before), so dropping the offset yields naive UTC, matching the
    generation feed.
    """
    grouped = transform.collapse_price_providers(pd.read_csv(config.PRICE_CSV))

    grouped["startTime"] = pd.to_datetime(grouped["startTime"], utc=True).dt.tz_localize(None)
    grouped = grouped.merge(time_lookup, left_on="startTime", right_on="datetime")
    grouped = grouped[["time_id", "price"]].drop_duplicates(subset="time_id")

    copy_frame(engine, "price", grouped)


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

    copy_frame(engine, "commodity_price", pd.concat(frames, ignore_index=True))


def build_database(database_url=None):
    """Truncate and repopulate every table. Returns the URL written to."""
    database_url = database_url or config.DATABASE_URL
    engine = create_engine(database_url)

    truncate_all(engine)
    load_fuel(engine)
    time_lookup = load_time_and_generation(engine)
    load_demand(engine, time_lookup)
    load_price(engine, time_lookup)
    load_commodity(engine)

    engine.dispose()
    return database_url


def main():
    parser = argparse.ArgumentParser(description="Rebuild the merit-order database.")
    parser.add_argument("--database-url", default=None, help="Target database URL.")
    args = parser.parse_args()

    print(f"built: {build_database(args.database_url)}")


if __name__ == "__main__":
    main()
