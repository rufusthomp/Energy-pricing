"""Source European bidding-zone data from the ENTSO-E Transparency Platform.

Same pattern as `weather.py`: fetch once per (zone, dataset, year), cache to
`data/raw/entsoe/`, and let the database build read the cache. It matters more here than
anywhere else in the project, because this is the only source that is both rate-limited
(400 requests per minute per token) and slow, and because a full panel pull is thousands
of requests that nobody wants to repeat.

The cache holds the response **unaggregated**: every production type ENTSO-E reports,
including the consumption legs. Only the load step collapses those into categories. That
is what makes the wide `zone_generation` table an acceptable exception to the
store-as-observed rule, so do not aggregate on the way into the cache.

Requires a security token in `GBMO_ENTSOE_TOKEN`. Getting one is a manual, multi-day
process: register at https://transparency.entsoe.eu/, then email transparency@entsoe.eu
with "RESTful API access" in the subject and the registered address in the body. Access
arrives within three working days, after which the token is generated under account
settings.

    python -m gbmo.ingest.entsoe --verify           # check the currency assertions
    python -m gbmo.ingest.entsoe --start 2018 --end 2026
"""

import argparse
import datetime as dt
import os
import re
import time

import pandas as pd
from entsoe import EntsoePandasClient, EntsoeRawClient
from entsoe.exceptions import (
    InvalidBusinessParameterError,
    NoMatchingDataError,
    PaginationError,
)

from gbmo.config import RAW_DIR
from gbmo.ingest.zones import ZONES

CACHE_DIR = RAW_DIR / "entsoe"
TOKEN_ENV = "GBMO_ENTSOE_TOKEN"

DATASETS = ("price", "load", "generation")

MAX_ATTEMPTS = 4

# ENTSO-E publishes with a short lag and revises recent values, so the current year is
# clamped rather than requested up to the minute. Two days keeps the tail of the cache
# stable across re-runs; without it, every re-fetch rewrites the final partial day.
PUBLICATION_LAG_DAYS = 2

# Courtesy pause between requests. The documented limit is 400/minute, which this is
# nowhere near, but a full panel pull is thousands of sequential requests and there is
# nothing to gain from crowding a free public service.
REQUEST_PAUSE_SECONDS = 0.5

TIMEZONE_BY_ZONE = {z[0]: z[3] for z in ZONES}
CURRENCY_BY_ZONE = {z[0]: z[4] for z in ZONES}


class MissingToken(RuntimeError):
    pass


def _token():
    token = os.environ.get(TOKEN_ENV)
    if not token:
        raise MissingToken(
            f"No ENTSO-E token. Set {TOKEN_ENV} to a security token from\n"
            "https://transparency.entsoe.eu/ (see this module's docstring for how to\n"
            "request API access; it takes up to three working days)."
        )
    return token


def fetch_end_date(year, today=None):
    """Last date to request for a year: its end, or the publication lag boundary."""
    today = today or dt.datetime.now(dt.UTC).date()
    return min(dt.date(year, 12, 31), today - dt.timedelta(days=PUBLICATION_LAG_DAYS))


def request_window(zone, year):
    """Local-time bounds for a calendar year in the zone's own clock.

    entsoe-py requires tz-aware timestamps and interprets them literally, so localising
    to the zone rather than to UTC is what makes "2019" mean the zone's 2019 and not a
    window shifted by its offset. The GB pipeline was bitten once by treating local
    settlement dates as UTC; this is the same mistake in a different costume.
    """
    tz = TIMEZONE_BY_ZONE[zone]
    end = fetch_end_date(year)
    if end < dt.date(year, 1, 1):
        return None
    start = pd.Timestamp(f"{year}-01-01", tz=tz)
    # Exclusive upper bound, one day past the last date wanted
    return start, pd.Timestamp(end + dt.timedelta(days=1), tz=tz)


def flatten_generation_columns(frame):
    """Collapse entsoe-py's MultiIndex generation columns to flat, readable names.

    When a production type reports both directions (pumped storage is the obvious case)
    the client returns ('Hydro Pumped Storage', 'Actual Aggregated') and
    ('Hydro Pumped Storage', 'Actual Consumption'). Both are kept: the consumption leg is
    the incumbent arbitrageur charging, which is the closest thing in the data to what
    this project's batteries are doing.
    """
    if not isinstance(frame.columns, pd.MultiIndex):
        return frame

    names = []
    for production_type, direction in frame.columns:
        if str(direction).strip().lower() == "actual consumption":
            names.append(f"{production_type} [consumption]")
        else:
            names.append(production_type)
    frame = frame.copy()
    frame.columns = names
    # A zone can report the same type twice across a year boundary; keep the first
    return frame.loc[:, ~pd.Index(names).duplicated()]


def to_utc_naive(frame):
    """Zone-local tz-aware index to naive UTC, matching every other table in this schema."""
    out = frame.copy()
    out.index = out.index.tz_convert("UTC").tz_localize(None)
    out.index.name = "datetime"
    return out


def resolution_minutes(index):
    """Native publication resolution, inferred from the modal gap between observations.

    Modal rather than minimum, because DST transitions and single missing hours both
    produce gaps that are not the resolution. Returns 60 for an empty or single-row
    index, which only occurs for a zone-year with no usable data.
    """
    if len(index) < 2:
        return 60
    gaps = pd.Series(index).diff().dropna()
    if gaps.empty:
        return 60
    return int(gaps.mode().iloc[0].total_seconds() // 60)


def _call(client, dataset, zone, start, end):
    if dataset == "price":
        return client.query_day_ahead_prices(zone, start=start, end=end).to_frame("price")
    if dataset == "load":
        loaded = client.query_load(zone, start=start, end=end)
        # The client names this column 'Actual Load' in current versions and has renamed
        # it before; take the first column rather than trusting the label.
        return loaded.iloc[:, [0]].set_axis(["mw"], axis=1)
    if dataset == "generation":
        return flatten_generation_columns(client.query_generation(zone, start=start, end=end))
    raise ValueError(f"unknown dataset {dataset!r}")


def fetch(client, dataset, zone, year, retries=MAX_ATTEMPTS):
    """One zone-year of one dataset, as a naive-UTC frame. None if nothing is published.

    A zone-year genuinely having no data is normal and not an error: DE_LU does not exist
    before October 2018, several zones began reporting generation late, and the current
    year runs out partway through. Those return None. Transport failures retry.
    """
    window = request_window(zone, year)
    if window is None:
        return None
    start, end = window

    for attempt in range(1, retries + 1):
        try:
            frame = _call(client, dataset, zone, start, end)
        except (NoMatchingDataError, InvalidBusinessParameterError):
            return None  # the platform holds nothing here; retrying cannot change that
        except PaginationError:
            raise  # a request too large to serve is a bug in the chunking, not a blip
        # Broad by necessity: entsoe-py lets requests' own exceptions through
        # unwrapped, and every one of them is a transport failure worth retrying.
        except Exception as exc:
            if attempt == retries:
                raise RuntimeError(
                    f"{zone} {year} {dataset}: giving up after {retries} attempts "
                    f"({type(exc).__name__}: {exc})"
                ) from exc
            time.sleep(3 * attempt)
            continue

        if frame is None or frame.empty:
            return None
        return to_utc_naive(frame).sort_index()

    return None


def cache_path(dataset, zone, year):
    return CACHE_DIR / dataset / f"{zone}_{year}.csv"


def populate_cache(start_year, end_year, zones=None, datasets=DATASETS, force=False):
    """Fill the CSV cache, skipping anything already present."""
    client = EntsoePandasClient(api_key=_token())
    zones = zones or [z[0] for z in ZONES]
    fetched = skipped = empty = 0

    for dataset in datasets:
        (CACHE_DIR / dataset).mkdir(parents=True, exist_ok=True)
        for zone in zones:
            for year in range(start_year, end_year + 1):
                path = cache_path(dataset, zone, year)
                if path.exists() and not force:
                    skipped += 1
                    continue
                frame = fetch(client, dataset, zone, year)
                time.sleep(REQUEST_PAUSE_SECONDS)
                if frame is None:
                    empty += 1
                    continue
                frame.to_csv(path)
                fetched += 1
                print(f"  {dataset:<10} {zone:<8} {year}: {len(frame):,} rows "
                      f"@ {resolution_minutes(frame.index)}min")

    print(f"cached {fetched} zone-years, {skipped} already present, {empty} with no data")


def read_cache_years(dataset, zone, start_year, end_year):
    """Yield (year, frame) for each cached year, in order.

    Kept separate from `read_cache` because the native publication resolution is a
    property of a zone-year, not of a zone: a zone that moved to a 15-minute market time
    unit in 2025 has both resolutions in its history, and the ingest manifest has to
    record which is which.
    """
    for year in range(start_year, end_year + 1):
        path = cache_path(dataset, zone, year)
        if path.exists():
            yield year, pd.read_csv(path, index_col="datetime", parse_dates=["datetime"])


def read_cache(dataset, zone, start_year, end_year):
    """Every cached year for one zone and dataset, concatenated. None if nothing cached."""
    frames = [f for _, f in read_cache_years(dataset, zone, start_year, end_year)]
    if not frames:
        return None
    out = pd.concat(frames).sort_index()
    # Year boundaries overlap by an hour where a zone's local year starts before UTC's
    return out[~out.index.duplicated(keep="first")]


CURRENCY_PATTERN = re.compile(r"<currency_Unit\.name>([A-Z]{3})</currency_Unit\.name>")


def verify_currencies(zones=None, probe_year=2023):
    """Check the currency asserted in `zones.py` against what the platform publishes.

    The zone dimension carries a currency because it is a property of the market rather
    than of the hour, but that makes it an assertion sitting in a Python list where
    nothing would ever contradict it. Comparing euros to zloty in a panel regression
    fails silently and looks like a finding, so the assertion is checked against one day
    of raw XML per zone before the first load.

    Returns a list of (zone, asserted, published) mismatches, empty when all agree.
    """
    client = EntsoeRawClient(api_key=_token())
    zones = zones or [z[0] for z in ZONES]
    mismatches = []

    for zone in zones:
        tz = TIMEZONE_BY_ZONE[zone]
        start = pd.Timestamp(f"{probe_year}-06-01", tz=tz)
        try:
            xml = client.query_day_ahead_prices(zone, start=start,
                                                end=start + pd.Timedelta(days=1))
        except NoMatchingDataError:
            print(f"  {zone:<8} no price data at {probe_year}-06-01, not checked")
            continue
        time.sleep(REQUEST_PAUSE_SECONDS)

        found = CURRENCY_PATTERN.search(xml)
        published = found.group(1) if found else None
        asserted = CURRENCY_BY_ZONE[zone]
        if published != asserted:
            mismatches.append((zone, asserted, published))
            print(f"  {zone:<8} MISMATCH: zones.py says {asserted}, platform says {published}")
        else:
            print(f"  {zone:<8} {published}")

    return mismatches


def main():
    parser = argparse.ArgumentParser(description="Populate the ENTSO-E cache.")
    parser.add_argument("--start", type=int, default=2018)
    parser.add_argument("--end", type=int, default=2026)
    parser.add_argument("--zones", nargs="*", default=None, help="Default: every panel zone.")
    parser.add_argument("--datasets", nargs="*", default=list(DATASETS))
    parser.add_argument("--force", action="store_true", help="Re-fetch cached zone-years.")
    parser.add_argument("--verify", action="store_true",
                        help="Only check the currency assertions, fetch nothing.")
    args = parser.parse_args()

    try:
        if args.verify:
            if verify_currencies(args.zones):
                raise SystemExit("Currency assertions in zones.py do not match the platform.")
            print("all currency assertions hold")
            return
        populate_cache(args.start, args.end, args.zones, args.datasets, force=args.force)
    except MissingToken as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
