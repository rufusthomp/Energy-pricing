"""Backtest the information operators across the European panel.

Implements the operators fixed in docs/preregistration.md. Each is the same MILP as the
perfect-foresight ceiling, optimised on a different information set and settled at the
day's actual prices, so the gap between any two operators is a pure difference in
information:

    lp_perfect_foresight   the day's own prices             -> the ceiling V*
    typical_day            mean price by market hour, d-28..d-1
    persistence            day d-1's prices, by market hour

A day is the auction's CET delivery day (23, 24 or 25 hours), not the zone's civil day,
and the battery starts and ends each one empty. Output goes to `model.daily_result`, one
row per run, zone and day. Per-period dispatch is not stored for the panel
(docs/data-scaling.md).

    python -m gbmo.arbitrage.panel [--zones DK_1 ES ...] [--workers 12]

Re-running replaces earlier panel runs of the same strategy and battery, so the table
holds one current answer per operator rather than a history nobody asked for.
"""

import argparse
import datetime as dt
import io
import json
import multiprocessing as mp
import time

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from gbmo import config
from gbmo.arbitrage import lp
from gbmo.arbitrage.backtest import git_commit
from gbmo.ingest.zones import ZONE_CODES

# GB has no ENTSO-E prices after 2020. IE_SEM has almost no load forecast after mid-2021,
# so its penetration regressors are undefined. Both exclusions are pre-registered.
PANEL_ZONES = [z for z in ZONE_CODES if z not in ("GB", "IE_SEM")]

FIRST_DAY = pd.Timestamp("2019-01-01")
LAST_DAY = pd.Timestamp("2026-09-20")

PERIOD_HOURS = 1.0

TD_WINDOW_DAYS = 28
# The typical-day profile needs most of its window, or on the days after a data gap it
# is an average of a handful of days and stops being "typical". 20 of 28 is the floor.
TD_MIN_DAYS = 20

STRATEGIES = ("lp_perfect_foresight", "typical_day", "persistence")

# Tolerance for the physical checks on every schedule, matching arbitrage.validate
TOLERANCE = 1e-6

PRICES = """
    SELECT c.delivery_date, p.datetime, p.price,
           EXTRACT(HOUR FROM (p.datetime AT TIME ZONE 'UTC') AT TIME ZONE z.market_timezone)::int
               AS market_hour
    FROM entsoe.price p
    JOIN entsoe.calendar c USING (zone_id, datetime)
    JOIN ref.zone z USING (zone_id)
    WHERE z.code = :code AND c.delivery_date BETWEEN :start AND :end
    ORDER BY p.datetime
"""

# The calendar is a complete hour grid, so its count per delivery day is the number of
# hours that day should have: 23, 24 or 25.
EXPECTED_HOURS = """
    SELECT c.delivery_date, count(*) AS expected
    FROM entsoe.calendar c JOIN ref.zone z USING (zone_id)
    WHERE z.code = :code AND c.delivery_date BETWEEN :start AND :end
    GROUP BY c.delivery_date
"""


def complete_days(prices, expected):
    """{delivery_date: frame} for every day whose hours are all priced.

    A day with a missing hour is not a smaller version of the arbitrage problem, it is a
    different one, so it is dropped rather than interpolated.
    """
    counts = prices.groupby("delivery_date").size()
    expected = expected.set_index("delivery_date")["expected"]
    ok = counts.index[(counts == expected.reindex(counts.index)) & counts.between(23, 25)]
    return {d: g.reset_index(drop=True) for d, g in prices[prices["delivery_date"].isin(ok)]
            .groupby("delivery_date")}


def typical_day_profile(days, day, window=TD_WINDOW_DAYS, minimum=TD_MIN_DAYS):
    """Mean price by market hour over the complete days in [day - window, day - 1].

    None when fewer than `minimum` of those days are complete. The mean by market hour
    handles clock changes on its own: a 23-hour day contributes nothing to hour 2, and a
    25-hour day contributes both of its hour-2 prices.
    """
    # datetime.timedelta, not pd.Timedelta: date - pd.Timedelta is a Timestamp, which
    # never matches the datetime.date keys of `days`
    history = [days[day - dt.timedelta(days=k)] for k in range(1, window + 1)
               if day - dt.timedelta(days=k) in days]
    if len(history) < minimum:
        return None
    return pd.concat(history).groupby("market_hour")["price"].mean()


def persistence_profile(days, day):
    """Day d-1's prices by market hour. None if d-1 is not a complete day.

    A repeated hour (autumn clock change) is averaged. A missing one (spring) is filled by
    linear interpolation between its neighbours when the profile is mapped onto day d.
    """
    previous = day - dt.timedelta(days=1)
    if previous not in days:
        return None
    return days[previous].groupby("market_hour")["price"].mean()


def forecast_for(profile, day_frame):
    """Map a by-hour profile onto a day's hours, interpolating any hour it lacks."""
    full = profile.reindex(range(24)).interpolate(limit_direction="both")
    return full.reindex(day_frame["market_hour"]).to_numpy()


def settle(schedule, actual, spec):
    """Revenue of a schedule at actual prices, with the physical limits asserted."""
    charge, discharge, soc = schedule.charge_mw, schedule.discharge_mw, schedule.soc_mwh
    if (soc.max() > spec.capacity_mwh + TOLERANCE or soc.min() < spec.min_soc_mwh - TOLERANCE
            or max(charge.max(), discharge.max()) > spec.power_mw + TOLERANCE):
        raise ValueError(f"schedule for {spec.name} breaks a physical limit")
    return {
        "revenue": float(PERIOD_HOURS * np.dot(actual, discharge - charge)),
        "charged_mwh": float(PERIOD_HOURS * charge.sum()),
        "discharged_mwh": float(PERIOD_HOURS * discharge.sum()),
        "min_soc_mwh": float(soc.min()),
        "max_soc_mwh": float(soc.max()),
    }


def run_zone(args):
    """Every operator and battery for one zone. Runs in a worker process."""
    code, specs, database_url, *mode = args
    td14_only = bool(mode and mode[0] == "td14")
    engine = create_engine(database_url)
    start = FIRST_DAY - pd.Timedelta(days=TD_WINDOW_DAYS + 1)
    params = {"code": code, "start": start.date(), "end": LAST_DAY.date()}
    prices = pd.read_sql(text(PRICES), engine, params=params)
    expected = pd.read_sql(text(EXPECTED_HOURS), engine, params=params)
    engine.dispose()

    days = complete_days(prices, expected)
    rows, failures = [], 0
    for day in pd.date_range(FIRST_DAY, LAST_DAY).date:
        if day not in days:
            continue
        frame = days[day]
        actual = frame["price"].to_numpy()
        td, ps = typical_day_profile(days, day), persistence_profile(days, day)

        for spec in specs:
            if td14_only:
                # The pre-registered 14-day window, with the 20-of-28 completeness rule
                # scaled to 10 of 14
                td14 = typical_day_profile(days, day, window=14, minimum=10)
                plans = {} if td14 is None else {"typical_day_14": forecast_for(td14, frame)}
            else:
                plans = {"lp_perfect_foresight": actual}
            if td is not None and not td14_only:
                plans["typical_day"] = forecast_for(td, frame)
            if ps is not None and not td14_only:
                plans["persistence"] = forecast_for(ps, frame)

            for strategy, plan_prices in plans.items():
                schedule = lp.solve_day(plan_prices, spec, period_hours=PERIOD_HOURS)
                if not schedule.ok:
                    failures += 1
                    continue
                rows.append({"strategy": strategy, "battery": spec.name,
                             "zone": code, "delivery_date": day,
                             **settle(schedule, actual, spec)})
    return code, pd.DataFrame(rows), failures, len(days)


def load_specs(engine):
    frame = pd.read_sql("SELECT * FROM model.battery_spec ORDER BY capacity_mwh", engine)
    return [lp.BatterySpec(name=r["name"], power_mw=float(r["power_mw"]),
                           capacity_mwh=float(r["capacity_mwh"]),
                           round_trip_efficiency=float(r["round_trip_efficiency"]),
                           min_soc_mwh=float(r["min_soc_mwh"]))
            for _, r in frame.iterrows()]


def write(engine, results, zones, failures, config_extra=None):
    """One model.run per (strategy, battery), daily rows beneath. Replaces earlier runs."""
    ids = dict(pd.read_sql("SELECT code, zone_id FROM ref.zone", engine).itertuples(index=False))
    results = results.assign(zone_id=results["zone"].map(ids))
    commit = git_commit()

    with engine.begin() as con:
        for (strategy, battery), group in results.groupby(["strategy", "battery"]):
            con.execute(text("""
                DELETE FROM model.run r USING model.strategy s, model.battery_spec b
                WHERE r.strategy_id = s.strategy_id AND r.battery_id = b.battery_id
                  AND r.price_source = 'entsoe_day_ahead'
                  AND s.name = :strategy AND b.name = :battery
            """), {"strategy": strategy, "battery": battery})
            run_id = con.execute(text("""
                INSERT INTO model.run (strategy_id, battery_id, git_commit, config, seed,
                                       period_start, period_end, solver_status, price_source)
                SELECT s.strategy_id, b.battery_id, :commit, CAST(:config AS jsonb), NULL,
                       :start, :end, :status, 'entsoe_day_ahead'
                FROM model.strategy s, model.battery_spec b
                WHERE s.name = :strategy AND b.name = :battery
                RETURNING run_id
            """), {
                "commit": commit, "strategy": strategy, "battery": battery,
                "config": json.dumps({
                    "zones": zones, "period_hours": PERIOD_HOURS, "day": "CET delivery day",
                    "td_window_days": TD_WINDOW_DAYS, "td_min_days": TD_MIN_DAYS,
                    "initial_soc_mwh": 0.0, "final_soc_mwh": 0.0,
                    "zone_days": len(group), "solver_failures": failures,
                    **(config_extra or {}),
                }),
                "start": FIRST_DAY, "end": LAST_DAY + pd.Timedelta(days=1),
                "status": "optimal" if failures == 0 else f"{failures} solve(s) failed",
            }).scalar_one()

            out = group[["zone_id", "delivery_date", "revenue", "charged_mwh",
                         "discharged_mwh", "min_soc_mwh", "max_soc_mwh"]].copy()
            out.insert(0, "run_id", run_id)
            buf = io.StringIO()
            out.to_csv(buf, index=False, header=False)
            buf.seek(0)
            raw = con.connection.driver_connection
            with raw.cursor() as cur, cur.copy(
                f"COPY model.daily_result ({', '.join(out.columns)}) FROM STDIN WITH (FORMAT csv)"
            ) as copy:
                copy.write(buf.read())
            print(f"  run {run_id}: {strategy:<22} {battery:<8} {len(out):>7,} zone-days")


def main():
    parser = argparse.ArgumentParser(description="Backtest the panel operators.")
    parser.add_argument("--zones", nargs="*", default=PANEL_ZONES)
    parser.add_argument("--workers", type=int, default=min(12, mp.cpu_count()))
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--td14", action="store_true",
                        help="Only the pre-registered 14-day typical-day check, 2h battery.")
    args = parser.parse_args()

    url = args.database_url or config.DATABASE_URL
    engine = create_engine(url)
    specs = load_specs(engine)
    mode = "td14" if args.td14 else "all"
    if args.td14:
        specs = [s for s in specs if s.name.startswith("2h")]

    started = time.perf_counter()
    frames, failures = [], 0
    with mp.Pool(args.workers) as pool:
        for code, frame, failed, n_days in pool.imap_unordered(
                run_zone, [(z, specs, url, mode) for z in args.zones]):
            frames.append(frame)
            failures += failed
            print(f"  {code:<8} {n_days:>5,} complete days, {len(frame):>7,} results, "
                  f"{failed} failed  ({time.perf_counter() - started:5.0f}s)", flush=True)

    results = pd.concat(frames, ignore_index=True)
    extra = {"td_window_days": 14, "td_min_days": 10} if args.td14 else None
    write(engine, results, args.zones, failures, config_extra=extra)
    engine.dispose()
    print(f"done in {time.perf_counter() - started:.0f}s")


if __name__ == "__main__":
    main()
