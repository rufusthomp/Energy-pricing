"""Rebuild the database from raw sources in one run.

`schema.sql` is the source of truth for the structure and this module is the only thing
that populates it. The build is disposable and reproducible: the schema drops and
recreates every table, so re-running is always safe and never leaves a half-migrated
state. (That property is what changes when live ingest arrives; at that point the drops
move behind migrations.)

Run as a module so package imports resolve:

    python -m gbmo.ingest.load [--db PATH]
"""

import argparse
import sqlite3

import pandas as pd

from gbmo import config
from gbmo.ingest import reference, transform

# CPS is synthesised rather than sourced, so it needs an explicit end. It covers every
# month in the modelled span so the query never hits a missing top-up.
CPS_END_YEAR = 2027

PENCE_PER_KWH = "pence_per_kWh_GCV"
GBP_PER_TCO2 = "GBP_per_tCO2"


def load_fuel(con):
    """The hand-curated modelling layer."""
    con.executemany(reference.INSERT_FUELS, reference.FUELS)


def load_time_and_generation(con):
    """Wide NESO generation mix -> `time` dimension + long `generation` fact.

    Returns the time lookup, which the demand and price loaders both need.
    """
    df = pd.read_csv(config.GENERATION_CSV)
    df = df.drop(columns=reference.GENERATION_DERIVED_COLUMNS, axis=1)

    time_df = transform.build_time_dimension(df["DATETIME"])
    time_df.to_sql("time", con, if_exists="append", index=False)

    # Wide -> long: one column per fuel becomes one row per (time, fuel)
    df = pd.melt(df, id_vars="DATETIME", var_name="name", value_name="mw")

    fuel_lookup = pd.read_sql("SELECT fuel_id, name FROM fuel", con)
    time_lookup = pd.read_sql("SELECT time_id, datetime FROM time", con)

    df = df.merge(time_lookup, left_on="DATETIME", right_on="datetime")
    df = df.merge(fuel_lookup, on="name")

    df = df[["time_id", "fuel_id", "mw"]]
    df.to_sql("generation", con, if_exists="append", index=False)

    return time_lookup


def load_demand(con, time_lookup):
    """18 per-year NESO demand files -> `demand`."""
    # Sorted so a rebuild is deterministic; glob order is otherwise filesystem-dependent.
    demand_files = sorted(config.DEMAND_DIR.glob(config.DEMAND_GLOB))
    demand_df = pd.concat([pd.read_csv(f) for f in demand_files], ignore_index=True)

    # Settlement date + period -> timestamp. Periods are 1-indexed half hours.
    demand_df["datetime"] = (
        pd.to_datetime(demand_df["SETTLEMENT_DATE"])
        + pd.to_timedelta((demand_df["SETTLEMENT_PERIOD"] - 1) * 30, unit="m")
    ).dt.strftime("%Y-%m-%dT%H:%M:%S")

    demand_df = demand_df.merge(time_lookup, on="datetime")
    demand_df = demand_df[["time_id", "ND", "TSD"]]
    demand_df.columns = demand_df.columns.str.lower()  # Fit naming schema
    # Clock-change days produce duplicate timestamps
    demand_df = demand_df.drop_duplicates(subset="time_id")

    demand_df.to_sql("demand", con, if_exists="append", index=False)


def load_price(con, time_lookup):
    """Cached Elexon MID pull -> `price`, one volume-weighted price per period."""
    price_df = pd.read_csv(config.PRICE_CSV)
    grouped = transform.collapse_price_providers(price_df)

    grouped["startTime"] = pd.to_datetime(grouped["startTime"]).dt.strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    grouped = grouped.merge(time_lookup, left_on="startTime", right_on="datetime")
    grouped = grouped[["time_id", "price"]]
    grouped = grouped.drop_duplicates(subset="time_id")

    grouped.to_sql("price", con, if_exists="append", index=False)


def load_commodity(con):
    """Gas, coal, carbon and FX series -> `commodity_price`.

    Every series is loaded as observed, on a monthly grain, and kept separate from every
    other one. The EUA->UKA splice, whether CPS is added, and QEP vs SAP for gas are all
    modelling choices made at query time, so nothing here is pre-combined. The one
    conversion applied is EUR->GBP on the EUA series, which is a unit change, not a
    modelling choice — the FX series itself is loaded too so that step stays auditable.
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

    pd.concat(frames, ignore_index=True).to_sql(
        "commodity_price", con, if_exists="append", index=False
    )


def build_database(db_path=None):
    """Drop, recreate and repopulate every table. Returns the path written."""
    db_path = db_path or config.DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    schema_sql = config.SCHEMA_PATH.read_text()

    con = sqlite3.connect(db_path)
    try:
        con.executescript(schema_sql)
        load_fuel(con)
        time_lookup = load_time_and_generation(con)
        load_demand(con, time_lookup)
        load_price(con, time_lookup)
        load_commodity(con)
        con.commit()
    finally:
        con.close()

    return db_path


def main():
    parser = argparse.ArgumentParser(description="Rebuild the merit-order database.")
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Target database path (defaults to data/gb-merit-order.db).",
    )
    args = parser.parse_args()

    from pathlib import Path

    path = build_database(Path(args.db) if args.db else None)
    print(f"built: {path}")


if __name__ == "__main__":
    main()
