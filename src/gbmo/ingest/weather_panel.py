"""Source hourly ERA5 reanalysis weather for the European bidding-zone panel.

Same pattern as `weather.py` (Open-Meteo archive, no key, cache-then-load) extended to
19 zones and ~5-8 points each: 105 points in `gbmo.ingest.weather_points.POINTS`. A
referee asked for an instrument built from actual weather rather than the TSO forecast
wind and solar penetration the paper already treats on, so this pulls wind speed at 100m
(turbine hub height) and shortwave radiation at points chosen to sit on each zone's wind
and solar fleets. See `weather_points.py` for what each point represents and why.

## The free tier is the binding constraint, not wall-clock time

Open-Meteo's published limits are per-minute (600), per-hour (5,000) and per-day
(10,000), but those are *weighted call credits*, not HTTP requests: "a request for 2
weeks of data with 15 variables is 1.5 calls, 4 weeks is 3.0" (open-meteo.com/en/pricing).
Read literally, credit cost scales with `days_requested / 14` once the request exceeds
the 10-variable baseline is not triggered here (only 2 variables are requested, so the
variable multiplier stays 1), so a single request's cost is `days / 14` regardless of
how many years it is chunked into. Measured against one point (Horns Rev, 2019, full
year, 2 variables): the HTTP round trip is fast (~0.2s, no rate-limit headers returned
for anonymous use) but the year itself already costs 8760/24/14 =~ 26 credits. The full
period (2018-12-01 to 2026-09-21, 2,852 days) is therefore ~204 credits *per point*, and
the full 105-point panel is ~21,400 credits: over two days' quota even before accounting
for anything else calling the same free service. `priority_order` below is what makes a
partial run useful rather than an arbitrary subset: it round-robins the first four points
of every zone before touching any zone's fifth point, so a quota-limited run still leaves
every zone with its core coverage rather than fully covering a few zones and skipping the
rest.

Pacing (`RateTracker`) throttles to a fraction of the documented minute/hour ceilings
(never the full ceiling: this is a shared free service, and the published numbers are
Open-Meteo's stated ceiling, not a guarantee this client should aim for). The day budget
is enforced by refusing to *start* a point whose full-period cost would not fit in what
is left of the run's `--budget-credits` allowance; a point already in flight always
finishes chunk-by-chunk rather than being abandoned partway, since a partial-point cache
file is not written (see `fetch_point`).

Run standalone:

    python -m gbmo.ingest.weather_panel [--zones DK_1 DE_LU ...] [--budget-credits N]

Never refetches a point whose cache file already exists at
`data/raw/weather_panel/{zone}_{point}.csv`; delete the file to force a re-pull.
"""

import argparse
import datetime as dt
import time

import pandas as pd
import requests
from sqlalchemy import create_engine, text

from gbmo import config
from gbmo.config import RAW_DIR
from gbmo.ingest.load import copy_frame
from gbmo.ingest.weather_points import POINTS_BY_ZONE, ZONE_CODES_WITH_POINTS

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
CACHE_DIR = RAW_DIR / "weather_panel"

VARIABLES = ("wind_speed_100m", "shortwave_radiation")

# The period asked for. Not in config.py: this is a property of the weather instrument,
# not of the GB or ENTSO-E builds, and nothing else in the project needs it.
START_DATE = dt.date(2018, 12, 1)
END_DATE = dt.date(2026, 9, 21)

# Same reasoning as weather.py: the archive trails real time while observations are
# assimilated, so dates inside the lag window return a 400 rather than serve partial data.
ARCHIVE_LAG_DAYS = 7

# --- Open-Meteo's documented call-cost model (open-meteo.com/en/pricing) ----------------
# "A request for 2 weeks of data with 15 variables is 1.5 API calls, 4 weeks is 3.0":
# cost = (days / 14) * max(1, variables / 10). Only 2 variables are requested here, well
# under the 10-variable baseline, so the variable factor is always 1 and cost is driven
# by days alone. This is what "measure the real cost with one point first" resolved to:
# there is no per-response rate-limit header (checked empirically), so the cost has to be
# computed from the published formula rather than read off a response.
CALL_COST_BASELINE_DAYS = 14
CALL_COST_BASELINE_VARIABLES = 10


def call_cost(days, variables=None):
    variables = len(VARIABLES) if variables is None else variables
    return (days / CALL_COST_BASELINE_DAYS) * max(1, variables / CALL_COST_BASELINE_VARIABLES)


TOTAL_DAYS = (END_DATE - START_DATE).days + 1
COST_PER_POINT = call_cost(TOTAL_DAYS)

# Published free-tier ceilings, and the fraction of each this client actually paces to.
# Never the full published number: this is a shared free service with no key, and the
# ceiling is Open-Meteo's stated limit before it starts refusing traffic, not a budget to
# spend in full.
FREE_TIER_PER_MINUTE = 600
FREE_TIER_PER_HOUR = 5_000
FREE_TIER_PER_DAY = 10_000

PACE_PER_MINUTE = 400   # 67% of the published minute ceiling
PACE_PER_HOUR = 3_500    # 70% of the published hour ceiling
DEFAULT_DAILY_BUDGET = 8_000  # 80% of the published day ceiling

# Points are prioritised 4 per zone before any zone gets a 5th-8th point (see module
# docstring), so under a quota-limited run every zone keeps its core coverage.
PRIORITY_TIER_SIZE = 4

MAX_ATTEMPTS = 5
RETRY_BASE_SECONDS = 5
RETRY_CAP_SECONDS = 120


def archive_end_date(reference=None):
    """Last date the archive can serve, clipped by the assimilation lag."""
    reference = reference or dt.datetime.now(dt.UTC).date()
    return min(END_DATE, reference - dt.timedelta(days=ARCHIVE_LAG_DAYS))


def cache_path(zone, point_id):
    return CACHE_DIR / f"{zone}_{point_id}.csv"


class RateTracker:
    """Paces requests to stay under a fraction of the per-minute and per-hour ceilings.

    A sliding log of (timestamp, credit_cost) pairs. `wait_and_record` blocks until
    admitting the next request would not push either trailing window over its budget,
    coarse-polling rather than computing an exact wake time because the windows overlap
    and an exact schedule is not worth the complexity here.
    """

    def __init__(self, per_minute=PACE_PER_MINUTE, per_hour=PACE_PER_HOUR):
        self.per_minute = per_minute
        self.per_hour = per_hour
        self._log = []

    def _prune(self, now):
        self._log = [(t, c) for t, c in self._log if now - t < 3600]

    def wait_and_record(self, cost, label=""):
        waited = False
        while True:
            now = time.monotonic()
            self._prune(now)
            minute_used = sum(c for t, c in self._log if now - t < 60)
            hour_used = sum(c for t, c in self._log)
            if minute_used + cost <= self.per_minute and hour_used + cost <= self.per_hour:
                self._log.append((now, cost))
                return
            if not waited:
                print(f"    pacing: waiting for rate-limit headroom before {label}")
                waited = True
            time.sleep(3)


def fetch_year_chunk(lat, lon, start_date, end_date, retries=MAX_ATTEMPTS):
    """One point-year (or partial year) of hourly data, with exponential backoff.

    Exponential rather than weather.py's linear backoff: that module's 502s are a slow,
    unloaded single-location endpoint's transient errors, but this module also has to
    survive a genuine 429 from having 105 points sharing one free-tier budget, and a
    fixed linear wait would spend every retry still inside a short-lived throttle.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "hourly": ",".join(VARIABLES),
        "timezone": "GMT",
    }
    last = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(ARCHIVE_URL, params=params, timeout=120)
        except requests.RequestException as exc:
            last = type(exc).__name__
        else:
            if response.status_code == 200:
                # A 200 with an empty or non-JSON body has been seen in practice; it is
                # transient, so retry it like a server error rather than crash the run
                try:
                    hourly = response.json()["hourly"]
                except (ValueError, KeyError):
                    last = "HTTP 200 with an unreadable body"
                else:
                    frame = pd.DataFrame(hourly).rename(columns={"time": "datetime"})
                    frame["datetime"] = pd.to_datetime(frame["datetime"])
                    return frame
            elif response.status_code == 429 or response.status_code >= 500:
                last = f"HTTP {response.status_code}"
            else:
                # 4xx other than 429 means the request itself is wrong; retrying cannot fix it
                raise RuntimeError(
                    f"HTTP {response.status_code} for ({lat}, {lon}) "
                    f"{start_date}..{end_date}: {response.text[:200]}"
                )
        wait = min(RETRY_CAP_SECONDS, RETRY_BASE_SECONDS * 2 ** (attempt - 1))
        print(f"    retry {attempt}/{retries} after {last}, backing off {wait}s")
        time.sleep(wait)
    raise RuntimeError(f"giving up on ({lat}, {lon}) {start_date}..{end_date} "
                       f"after {retries} attempts ({last})")


def fetch_point(zone, point_id, lat, lon, tracker):
    """The whole configured period for one point, chunked by year for reliability.

    Chunking does not change the total credit cost (cost is proportional to total days
    regardless of how many requests it is split across), only the reliability of any one
    response and the granularity `RateTracker` paces at. Written to the cache only once
    every year has succeeded, so a point that fails partway leaves no cache file and is
    retried from the start next run, never loaded half-complete.
    """
    frames = []
    for year in range(START_DATE.year, END_DATE.year + 1):
        year_start = max(START_DATE, dt.date(year, 1, 1))
        year_end = min(END_DATE, archive_end_date(), dt.date(year, 12, 31))
        if year_end < year_start:
            continue
        days = (year_end - year_start).days + 1
        cost = call_cost(days)
        tracker.wait_and_record(cost, label=f"{zone}/{point_id} {year}")
        frame = fetch_year_chunk(lat, lon, year_start, year_end)
        frames.append(frame)

    if not frames:
        return None
    out = pd.concat(frames, ignore_index=True).drop_duplicates(subset="datetime")
    out = out.sort_values("datetime").reset_index(drop=True)
    return out


def priority_order(zone_codes):
    """Points ordered so a quota-limited run covers every zone's core points first.

    Tier 1: index 0-3 of every zone, round-robined across zones (not exhausted zone by
    zone), so a run that stops partway through tier 1 still has *some* coverage of every
    zone rather than full coverage of the first zones and none of the rest. Tier 2: index
    4+ for zones with more than 4 points, same round-robin.
    """
    per_zone = {z: POINTS_BY_ZONE[z] for z in zone_codes}
    max_len = max(len(v) for v in per_zone.values())
    order = []
    for idx in range(min(PRIORITY_TIER_SIZE, max_len)):
        for zone in zone_codes:
            pts = per_zone[zone]
            if idx < len(pts):
                order.append((zone, *pts[idx]))
    for idx in range(PRIORITY_TIER_SIZE, max_len):
        for zone in zone_codes:
            pts = per_zone[zone]
            if idx < len(pts):
                order.append((zone, *pts[idx]))
    return order


def populate_cache(zones=None, budget_credits=DEFAULT_DAILY_BUDGET):
    """Fill the CSV cache, skipping anything already there. Returns (fetched, remaining).

    `remaining` is a list of (zone, point_id, reason) for points not fetched this run,
    either because the run's credit budget ran out or because the request itself failed
    after retries (a real error, reported rather than silently dropped).
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    zone_codes = zones or ZONE_CODES_WITH_POINTS
    unknown = [z for z in zone_codes if z not in POINTS_BY_ZONE]
    if unknown:
        raise ValueError(f"No weather points defined for zones: {unknown}")

    order = priority_order(zone_codes)
    tracker = RateTracker()
    used_credits = 0.0
    fetched, skipped, remaining = [], [], []

    for zone, point_id, lat, lon, role, description in order:
        path = cache_path(zone, point_id)
        if path.exists():
            skipped.append((zone, point_id))
            continue
        if used_credits + COST_PER_POINT > budget_credits:
            remaining.append((zone, point_id, "daily budget exhausted"))
            continue
        try:
            frame = fetch_point(zone, point_id, lat, lon, tracker)
        except RuntimeError as exc:
            print(f"  {zone}/{point_id}: FAILED ({exc})")
            remaining.append((zone, point_id, str(exc)))
            continue
        if frame is None or frame.empty:
            remaining.append((zone, point_id, "empty response"))
            continue
        frame.to_csv(path, index=False)
        used_credits += COST_PER_POINT
        fetched.append((zone, point_id))
        print(f"  {zone}/{point_id}: {len(frame):,} hours cached "
              f"(~{COST_PER_POINT:.0f} credits, {used_credits:.0f}/{budget_credits} used)")

    print(f"fetched {len(fetched)}, already cached {len(skipped)}, "
          f"not fetched {len(remaining)} of {len(order)} points")
    if remaining:
        print("not fetched:")
        for zone, point_id, reason in remaining:
            print(f"    {zone}/{point_id}: {reason}")
    return fetched, remaining


# --- Load: cache -> weather.observation --------------------------------------------------

WIND_RANGE = (0, 200)       # km/h, plausibility bound
RADIATION_RANGE = (0, 1100)  # W/m2, plausibility bound


def expected_hour_count():
    """Hours the configured period should hold, clipped by the archive lag."""
    end = archive_end_date()
    if end < START_DATE:
        return 0
    return (end - START_DATE).days * 24 + 24


def validate_frame(frame, zone, point_id):
    """Dedupe, range-check and report; never raises, since one bad point should not
    abort loading the other 100+."""
    issues = []
    before = len(frame)
    frame = frame.drop_duplicates(subset="datetime", keep="first")
    if len(frame) != before:
        issues.append(f"{before - len(frame)} duplicate hour(s) dropped")

    expected = expected_hour_count()
    if len(frame) != expected:
        issues.append(f"{len(frame):,} rows against {expected:,} expected")

    for column, (low, high) in (("wind_speed_100m", WIND_RANGE),
                                ("shortwave_radiation", RADIATION_RANGE)):
        out_of_range = ~frame[column].between(low, high) & frame[column].notna()
        if out_of_range.any():
            issues.append(f"{int(out_of_range.sum())} {column} value(s) outside "
                          f"[{low}, {high}], set to NULL")
            frame.loc[out_of_range, column] = None

    if issues:
        print(f"  {zone}/{point_id}: " + "; ".join(issues))
    return frame


def point_ids(engine):
    """{(zone_code, point): point_id} from the database, for mapping cache files to rows."""
    rows = pd.read_sql(
        "SELECT z.code AS zone_code, p.point, p.point_id "
        "FROM weather.point p JOIN ref.zone z USING (zone_id)",
        engine,
    )
    return {(r.zone_code, r.point): r.point_id for r in rows.itertuples(index=False)}


def load_observations(database_url=None, zones=None):
    """Load every cached point into weather.observation. Truncate-and-reload per point.

    Only points with a cache file are touched; a zone or point never fetched keeps
    whatever (possibly nothing) is already in the table for it, so a partial run never
    regresses previously loaded data.
    """
    database_url = database_url or config.DATABASE_URL
    engine = create_engine(database_url)
    ids = point_ids(engine)
    zone_codes = zones or ZONE_CODES_WITH_POINTS

    per_zone_rows = {}
    total = 0
    for zone in zone_codes:
        zone_rows = 0
        for point_id, lat, lon, role, description in POINTS_BY_ZONE.get(zone, []):
            path = cache_path(zone, point_id)
            if not path.exists():
                continue
            key = (zone, point_id)
            if key not in ids:
                print(f"  {zone}/{point_id}: cached but not in weather.point, skipped")
                continue

            frame = pd.read_csv(path, parse_dates=["datetime"])
            frame = validate_frame(frame, zone, point_id)
            out = frame[["datetime", "wind_speed_100m", "shortwave_radiation"]].copy()
            out.insert(0, "point_id", ids[key])

            with engine.begin() as con:
                con.execute(text("DELETE FROM weather.observation WHERE point_id = :pid"),
                           {"pid": ids[key]})
            copy_frame(engine, "weather.observation", out)
            zone_rows += len(out)

        per_zone_rows[zone] = zone_rows
        total += zone_rows
        if zone_rows:
            print(f"  {zone}: {zone_rows:,} rows loaded")

    engine.dispose()
    print(f"loaded {total:,} rows across {sum(1 for v in per_zone_rows.values() if v)} zones")
    return per_zone_rows


def main():
    parser = argparse.ArgumentParser(
        description="Fetch and load the European weather panel (ERA5 via Open-Meteo)."
    )
    parser.add_argument("--zones", nargs="*", default=None,
                        help="Zone codes to fetch/load (default: all 19 with points defined).")
    parser.add_argument("--budget-credits", type=float, default=DEFAULT_DAILY_BUDGET,
                        help="Estimated Open-Meteo call-credit ceiling for this run.")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--skip-fetch", action="store_true",
                        help="Load whatever is cached without hitting the API.")
    parser.add_argument("--skip-load", action="store_true",
                        help="Only populate the cache; do not write to the database.")
    args = parser.parse_args()

    if not args.skip_fetch:
        populate_cache(args.zones, budget_credits=args.budget_credits)
    if not args.skip_load:
        load_observations(args.database_url, args.zones)


if __name__ == "__main__":
    main()
