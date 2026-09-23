"""Load the ENTSO-E cache into the bidding-zone panel tables.

Deliberately a separate entry point from `load.py` rather than a step inside it. The GB
build truncates with RESTART IDENTITY on every run, which is safe for data that rebuilds
from local CSVs in four minutes; the panel is thousands of rate-limited requests, and
coupling the two would mean a routine GB reload could not be run without either
destroying the panel or re-fetching it.

    python -m gbmo.ingest.load_zones [--database-url URL]

The zone dimension (`ref.zone`) is upserted rather than truncated, so `zone_id` values
stay stable across reloads and model outputs that reference them stay valid. The `entsoe`
facts are rebuilt wholesale from the cache, and `entsoe.calendar` is refreshed after.
"""

import argparse
import datetime as dt

import pandas as pd
from sqlalchemy import create_engine, text

from gbmo import config
from gbmo.ingest import entsoe
from gbmo.ingest.load import copy_frame
from gbmo.ingest.zones import (
    CATEGORIES,
    CATEGORY_BY_PRODUCTION_TYPE,
    ZONE_IDS,
    ZONES,
    market_timezone,
)

FACT_TABLES = ("entsoe.price", "entsoe.load", "entsoe.generation", "entsoe.load_forecast",
               "entsoe.vre_forecast", "entsoe.capacity", "entsoe.ingest")

# Where each hourly dataset lands and which columns it keeps. Capacity is annual and is
# handled separately in `load_capacity`.
HOURLY_TARGETS = {
    "price":         ("entsoe.price", ["price"]),
    "load":          ("entsoe.load", ["mw"]),
    "generation":    ("entsoe.generation", [f"{c}_mw" for c in CATEGORIES]),
    "load_forecast": ("entsoe.load_forecast", ["mw"]),
    "vre_forecast":  ("entsoe.vre_forecast", ["wind_mw", "solar_mw"]),
}


class UnknownProductionType(RuntimeError):
    """A production type appeared that `zones.py` has no category for.

    Raised rather than warned because the consequence is silent and directional: an
    unmapped fuel is excluded from every category, which understates total generation and
    therefore inflates renewable share. Renewable share is the treatment variable in the
    panel, so a new ENTSO-E production type would quietly manufacture the finding this
    project is trying to test.
    """


def upsert_zones(engine):
    """Seed or refresh the zone dimension with the permanent ids in `zones.ZONE_IDS`.

    The id is written explicitly rather than left to the identity column, so every build
    assigns the same one. A conflict on `code` updates attributes but never the id; a zone
    whose stored id disagrees with ZONE_IDS fails the check below rather than drifting.
    """
    rows = [
        {"zone_id": ZONE_IDS[code], "code": code, "country_code": country, "name": name,
         "timezone": tz,
         "market_timezone": market_timezone(code), "currency": currency,
         "rationale": rationale}
        for code, country, name, tz, currency, rationale in ZONES
    ]
    statement = text("""
        INSERT INTO ref.zone
            (zone_id, code, country_code, name, timezone, market_timezone, currency, rationale)
        VALUES
            (:zone_id, :code, :country_code, :name, :timezone, :market_timezone, :currency,
             :rationale)
        ON CONFLICT (code) DO UPDATE SET
            country_code    = EXCLUDED.country_code,
            name            = EXCLUDED.name,
            timezone        = EXCLUDED.timezone,
            market_timezone = EXCLUDED.market_timezone,
            currency        = EXCLUDED.currency,
            rationale       = EXCLUDED.rationale
    """)
    with engine.begin() as con:
        con.execute(statement, rows)
        # Explicit ids leave the identity sequence behind; move it past them so a default
        # insert can never collide with a frozen id
        con.execute(text("""
            SELECT setval(pg_get_serial_sequence('ref.zone', 'zone_id'),
                          (SELECT max(zone_id) FROM ref.zone))
        """))
        stored = dict(con.execute(text("SELECT code, zone_id FROM ref.zone")).fetchall())
    drifted = {c: (stored[c], i) for c, i in ZONE_IDS.items() if stored.get(c) != i}
    if drifted:
        raise RuntimeError(f"ref.zone ids disagree with zones.ZONE_IDS (stored, expected): {drifted}")


def zone_ids(engine):
    return dict(pd.read_sql("SELECT code, zone_id FROM ref.zone", engine).itertuples(index=False))


def truncate_facts(engine):
    with engine.begin() as con:
        con.execute(text(f"TRUNCATE {', '.join(FACT_TABLES)}"))


def to_hourly(frame):
    """Resample to the hourly grain the panel is defined on, dropping empty hours.

    From October 2025 several zones publish day-ahead prices and generation on a
    15-minute market time unit rather than hourly. The mean is the right aggregate for
    both: a battery holding a flat position across the hour earns the mean of the
    quarters, and mean MW over an hour is the hour's energy in MWh.

    Resampling happens after the conversion to naive UTC, not before, so clock changes
    never produce a duplicated or missing local hour to reason about.
    """
    hourly = frame.resample("1h").mean()
    return hourly.dropna(how="all")


def aggregate_generation(frame, allow_unknown=False):
    """Collapse ENTSO-E production types into the seven panel categories.

    Consumption legs are excluded: they are withdrawals, not generation, and summing them
    into a category would net a pumped-storage zone's output against its own charging.
    They stay in the cache, where the arbitrage side of the project can reach them.
    """
    generation_columns = [c for c in frame.columns if not c.endswith("[consumption]")]
    unknown = [c for c in generation_columns if c not in CATEGORY_BY_PRODUCTION_TYPE]
    if unknown and not allow_unknown:
        raise UnknownProductionType(
            f"No category in zones.py for: {', '.join(sorted(unknown))}.\n"
            "Add them to CATEGORY_BY_PRODUCTION_TYPE, or pass --allow-unknown-types to\n"
            "exclude them knowingly (which understates total generation)."
        )

    out = pd.DataFrame(index=frame.index)
    for category in CATEGORIES:
        members = [c for c in generation_columns
                   if CATEGORY_BY_PRODUCTION_TYPE.get(c) == category]
        # NULL and 0.0 are different answers, so a category the zone never reports stays
        # NULL rather than becoming a zero the panel would treat as an observation.
        out[f"{category}_mw"] = (frame[members].sum(axis=1, min_count=1)
                                 if members else float("nan"))
    return out


def _manifest(zone_id, dataset, years, resolution=True):
    fetched_at = dt.datetime.now(dt.UTC).replace(tzinfo=None)
    return pd.DataFrame([{
        "zone_id": zone_id,
        "dataset": dataset,
        "year": year,
        "resolution_minutes": entsoe.resolution_minutes(cached.index) if resolution else None,
        "source_rows": len(cached),
        "fetched_at": fetched_at,
    } for year, cached in years])


def load_capacity(engine, zone, zone_id, start_year, end_year, allow_unknown):
    """Annual installed capacity -> `zone_capacity`, keyed on the requested year.

    The year comes from the cache file, never from the index: ENTSO-E stamps capacity at
    local midnight on 1 January, which is 31 December of the year before in UTC.
    """
    years = list(entsoe.read_cache_years("capacity", zone, start_year, end_year))
    if not years:
        return 0
    rows = []
    for year, cached in years:
        # A zone occasionally publishes a mid-year revision as a second row; take the
        # latest, which is the capacity that stood for most of the year it describes
        snapshot = aggregate_generation(cached.tail(1), allow_unknown=allow_unknown)
        snapshot.insert(0, "year", year)
        rows.append(snapshot)
    out = pd.concat(rows, ignore_index=True)
    out.insert(0, "zone_id", zone_id)
    copy_frame(engine, "entsoe.capacity", out[["zone_id", "year", *[f"{c}_mw" for c in CATEGORIES]]])
    copy_frame(engine, "entsoe.ingest", _manifest(zone_id, "capacity", years, resolution=False))
    return len(out)


def load_zone_dataset(engine, dataset, zone, zone_id, start_year, end_year, allow_unknown):
    """One zone and hourly dataset from cache to table. Returns rows written."""
    if dataset == "capacity":
        return load_capacity(engine, zone, zone_id, start_year, end_year, allow_unknown)

    years = list(entsoe.read_cache_years(dataset, zone, start_year, end_year))
    if not years:
        return 0
    manifest = _manifest(zone_id, dataset, years)

    raw = pd.concat([f for _, f in years]).sort_index()
    # Year files overlap by an hour wherever a zone's local year begins before UTC's
    raw = raw[~raw.index.duplicated(keep="first")]
    frame = to_hourly(raw)

    table, columns = HOURLY_TARGETS[dataset]
    if dataset in ("generation", "vre_forecast"):
        frame = aggregate_generation(frame, allow_unknown=allow_unknown)
    elif dataset in ("load", "load_forecast"):
        # Negative load is a reporting error rather than a real withdrawal, and the CHECK
        # constraint would reject the whole COPY. Drop it here so one bad hour in one
        # zone-year does not fail the load.
        frame = frame[frame["mw"] >= 0]
    frame = frame[columns].dropna(how="all")
    if frame.empty:
        return 0

    out = frame.reset_index()
    out.insert(0, "zone_id", zone_id)
    copy_frame(engine, table, out[["zone_id", "datetime", *columns]])
    copy_frame(engine, "entsoe.ingest", manifest)
    return len(out)


def build_panel(database_url=None, start_year=None, end_year=None, zones=None,
                allow_unknown=False):
    """Rebuild every panel fact table from the ENTSO-E cache. Returns the URL written to."""
    database_url = database_url or config.DATABASE_URL
    start_year = start_year or config.FIRST_PANEL_YEAR
    end_year = end_year or config.LAST_YEAR
    engine = create_engine(database_url)

    upsert_zones(engine)
    truncate_facts(engine)

    ids = zone_ids(engine)
    codes = zones or [z[0] for z in ZONES]
    total = 0

    for zone in codes:
        written = {}
        for dataset in entsoe.DATASETS:
            written[dataset] = load_zone_dataset(
                engine, dataset, zone, ids[zone], start_year, end_year, allow_unknown
            )
        total += sum(written.values())
        summary = ", ".join(f"{k} {v:,}" for k, v in written.items())
        print(f"  {zone:<8} {summary}")

    # The calendar's hour grid spans the first to last price, so it is rebuilt from
    # whatever was just loaded. Not CONCURRENTLY: nothing reads it mid-load.
    with engine.begin() as con:
        con.execute(text("REFRESH MATERIALIZED VIEW entsoe.calendar"))
        con.execute(text("ANALYZE"))
    engine.dispose()

    print(f"panel rebuilt: {total:,} rows across {len(codes)} zones")
    return database_url


def main():
    parser = argparse.ArgumentParser(description="Load the ENTSO-E cache into the panel.")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--start", type=int, default=None)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--zones", nargs="*", default=None)
    parser.add_argument("--allow-unknown-types", action="store_true",
                        help="Exclude unmapped production types instead of failing.")
    args = parser.parse_args()

    build_panel(args.database_url, args.start, args.end, args.zones,
                allow_unknown=args.allow_unknown_types)


if __name__ == "__main__":
    main()
