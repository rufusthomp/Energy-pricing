"""Source hourly reanalysis weather from the Open-Meteo archive.

Free, no key required. Fetched once per (location, year) and cached to
`data/raw/weather/`, so the API is hit once and a database rebuild reads the cache. That
is the same pattern the Elexon price pull already uses, and it matters more here: the
archive is slow enough that re-fetching on every reload would be painful, and the service
returns intermittent 502s that are only tolerable because the results are kept.

Run standalone to populate the cache:

    python -m gbmo.ingest.weather [--start 2018] [--end 2026]
"""

import argparse
import datetime as dt
import time

import pandas as pd
import requests

from gbmo.config import RAW_DIR

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
CACHE_DIR = RAW_DIR / "weather"

# Points chosen to stand in for where GB output and demand actually come from, not for
# geographic tidiness. Kept in step with the weather_location table in migration
# a305783f9fcc.
LOCATIONS = {
    "scotland": (57.00, -4.00),
    "north_sea": (54.50, 2.00),
    "irish_sea": (53.80, -3.50),
    "south": (51.00, -1.00),
    "london": (51.50, -0.13),
}

# Wind at 100m rather than 10m because that is roughly turbine hub height, and the
# relationship between hub-height wind and output is far tighter than at the surface.
VARIABLES = {
    "wind_speed_100m": "km/h",
    "shortwave_radiation": "W/m2",
    "temperature_2m": "degC",
}

MAX_ATTEMPTS = 5

# The archive trails real time while observations are assimilated. Asking for dates
# inside that window returns a 400, so the current year is clamped rather than requested
# in full.
ARCHIVE_LAG_DAYS = 7


def archive_end_date(year, today=None):
    """Last date the archive can serve for a year: its end, or the lag boundary.

    UTC rather than local time, because the archive publishes on a UTC boundary and the
    lag is defined against it.
    """
    today = today or dt.datetime.now(dt.UTC).date()
    return min(dt.date(year, 12, 31), today - dt.timedelta(days=ARCHIVE_LAG_DAYS))


def fetch_year(location, year, retries=MAX_ATTEMPTS):
    """One location-year of hourly data, retrying through the archive's transient 502s."""
    lat, lon = LOCATIONS[location]
    end = archive_end_date(year)
    if end < dt.date(year, 1, 1):
        return None  # entirely in the future

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": f"{year}-01-01",
        "end_date": end.isoformat(),
        "hourly": ",".join(VARIABLES),
        "timezone": "UTC",
    }

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(ARCHIVE_URL, params=params, timeout=120)
            if response.status_code == 200:
                hourly = response.json()["hourly"]
                frame = pd.DataFrame(hourly).rename(columns={"time": "datetime"})
                frame["datetime"] = pd.to_datetime(frame["datetime"])
                return frame.dropna()
            # 4xx means the request itself is wrong; retrying cannot fix it
            if 400 <= response.status_code < 500:
                raise RuntimeError(
                    f"{location} {year}: HTTP {response.status_code} - {response.text[:160]}")
            last = f"HTTP {response.status_code}"
        except requests.RequestException as exc:
            last = type(exc).__name__
        # Linear backoff is enough: these are transient gateway errors, not rate limits
        time.sleep(3 * attempt)

    raise RuntimeError(f"{location} {year}: giving up after {retries} attempts ({last})")


def cache_path(location, year):
    return CACHE_DIR / f"{location}_{year}.csv"


def populate_cache(start_year, end_year, force=False):
    """Fill the CSV cache, skipping anything already there."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fetched = skipped = 0

    for location in LOCATIONS:
        for year in range(start_year, end_year + 1):
            path = cache_path(location, year)
            if path.exists() and not force:
                skipped += 1
                continue
            frame = fetch_year(location, year)
            if frame is None or frame.empty:
                continue
            frame.to_csv(path, index=False)
            fetched += 1
            print(f"  {location} {year}: {len(frame):,} hours")
            time.sleep(1)  # courtesy pause; the free tier is generous but not unlimited

    print(f"cached {fetched} location-years, {skipped} already present")


def read_cache(start_year, end_year):
    """The cache as one long frame: (datetime, location, variable, value, unit)."""
    frames = []
    for location in LOCATIONS:
        for year in range(start_year, end_year + 1):
            path = cache_path(location, year)
            if not path.exists():
                continue
            wide = pd.read_csv(path, parse_dates=["datetime"])
            long = wide.melt(id_vars="datetime", var_name="variable", value_name="value")
            long["location"] = location
            frames.append(long)

    if not frames:
        raise FileNotFoundError(
            f"No weather cache under {CACHE_DIR}. Run python -m gbmo.ingest.weather first.")

    out = pd.concat(frames, ignore_index=True).dropna(subset=["value"])
    out["unit"] = out["variable"].map(VARIABLES)
    return out[["datetime", "location", "variable", "value", "unit"]]


def main():
    parser = argparse.ArgumentParser(description="Populate the weather cache.")
    parser.add_argument("--start", type=int, default=2018)
    parser.add_argument("--end", type=int, default=2026)
    parser.add_argument("--force", action="store_true", help="Re-fetch cached years.")
    args = parser.parse_args()
    populate_cache(args.start, args.end, force=args.force)


if __name__ == "__main__":
    main()
