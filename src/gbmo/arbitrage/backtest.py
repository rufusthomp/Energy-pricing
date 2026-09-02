"""Run a strategy across the history and record what it did.

One `model_run` row per (strategy, battery) covering the whole window, with a `dispatch`
row per settlement period beneath it. Every run records the commit, the configuration and
the seed that produced it, so a schedule can be traced back to the code that made it.

Only days where every settlement period carries a price are considered. Arbitraging
against a missing price is not a smaller version of the problem, it is a different one,
and silently interpolating would put invented numbers into the denominator that every
other strategy is scored against.

    python -m gbmo.arbitrage.backtest --strategy lp_perfect_foresight
"""

import argparse
import io
import json
import subprocess

import pandas as pd
from sqlalchemy import create_engine, text

from gbmo import config
from gbmo.arbitrage import heuristic, lp, validate

STRATEGIES = {
    "lp_perfect_foresight": lp.solve_day,
    "naive_tod": heuristic.solve_day,
}

PERIODS_PER_DAY = 48

# Only complete days. The generation feed is UTC, so every day is exactly 48 periods;
# the 46 and 50 period days exist only in the local-clock demand source.
COMPLETE_DAYS = f"""
    WITH complete AS (
        SELECT sp.date
        FROM settlement_period sp
        LEFT JOIN price p ON p.time_id = sp.time_id
        GROUP BY sp.date
        HAVING count(*) = {PERIODS_PER_DAY} AND count(p.time_id) = {PERIODS_PER_DAY}
    )
    SELECT sp.date, sp.time_id, sp.datetime, p.price
    FROM settlement_period sp
    JOIN price p ON p.time_id = sp.time_id
    JOIN complete c ON c.date = sp.date
    ORDER BY sp.datetime
"""


def git_commit():
    """The commit a run executed at, or 'unknown' outside a checkout."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=config.REPO_ROOT, text=True
        ).strip()
    except (subprocess.CalledProcessError, OSError):
        return "unknown"


def load_specs(engine):
    return pd.read_sql("SELECT * FROM battery_spec ORDER BY capacity_mwh", engine)


def load_prices(engine):
    return pd.read_sql(COMPLETE_DAYS, engine)


def run(engine, strategy_name, spec_row, prices, seed=None):
    """Solve every day for one battery, write the run, return its summary."""
    solve = STRATEGIES[strategy_name]
    spec = lp.BatterySpec(
        name=spec_row["name"],
        power_mw=float(spec_row["power_mw"]),
        capacity_mwh=float(spec_row["capacity_mwh"]),
        round_trip_efficiency=float(spec_row["round_trip_efficiency"]),
        min_soc_mwh=float(spec_row["min_soc_mwh"]),
    )

    frames, revenue, failures = [], 0.0, 0
    for _, day in prices.groupby("date", sort=True):
        result = solve(day["price"].to_numpy(), spec)
        if not result.ok:
            failures += 1
            continue
        revenue += result.revenue
        frames.append(pd.DataFrame({
            "time_id": day["time_id"].to_numpy(),
            "charge_mw": result.charge_mw,
            "discharge_mw": result.discharge_mw,
            "soc_mwh": result.soc_mwh,
        }))

    dispatch = pd.concat(frames, ignore_index=True)

    with engine.begin() as con:
        run_id = con.execute(
            text("""
                INSERT INTO model_run
                    (strategy_id, battery_id, git_commit, config, seed,
                     period_start, period_end, solver_status)
                SELECT s.strategy_id, :battery_id, :commit, CAST(:config AS jsonb), :seed,
                       :start, :end, :status
                FROM strategy s WHERE s.name = :strategy
                RETURNING run_id
            """),
            {
                "battery_id": int(spec_row["battery_id"]),
                "commit": git_commit(),
                "config": json.dumps({
                    "days": int(prices["date"].nunique()),
                    "periods_per_day": PERIODS_PER_DAY,
                    "initial_soc_mwh": 0.0,
                    "final_soc_mwh": 0.0,
                    "solver_failures": failures,
                }),
                "seed": seed,
                "start": prices["datetime"].min(),
                # Half-open [start, end): the end of the final period, not its start.
                # Using the last timestamp itself puts that period outside its own run.
                "end": prices["datetime"].max() + pd.Timedelta(minutes=30),
                "status": "optimal" if failures == 0 else f"{failures} day(s) failed",
                "strategy": strategy_name,
            },
        ).scalar_one()

    dispatch.insert(0, "run_id", run_id)
    _copy(engine, "dispatch", dispatch)

    # The physical limits are cross-table, so a CHECK cannot see them. This is where
    # they are actually enforced, and a run that fails here should not be trusted.
    validate.assert_valid(engine, run_id=run_id)

    return {"run_id": run_id, "strategy": strategy_name, "battery": spec.name,
            "duration_h": spec.duration_hours, "revenue": revenue, "failures": failures}


def _copy(engine, table, df):
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False, na_rep="")
    buf.seek(0)
    statement = f"COPY {table} ({', '.join(df.columns)}) FROM STDIN WITH (FORMAT csv)"
    raw = engine.raw_connection()
    try:
        with raw.driver_connection.cursor() as cur, cur.copy(statement) as copy:
            copy.write(buf.read())
        raw.commit()
    finally:
        raw.close()


def main():
    parser = argparse.ArgumentParser(description="Backtest a dispatch strategy.")
    parser.add_argument("--strategy", choices=[*STRATEGIES, "all"], default="all")
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args()

    engine = create_engine(args.database_url or config.DATABASE_URL)
    specs = load_specs(engine)
    prices = load_prices(engine)
    print(f"{prices['date'].nunique():,} complete days, "
          f"{len(prices):,} priced periods, {len(specs)} batteries")

    names = list(STRATEGIES) if args.strategy == "all" else [args.strategy]
    results = [run(engine, name, spec, prices)
               for name in names for _, spec in specs.iterrows()]

    print()
    print(pd.DataFrame(results).to_string(index=False))
    engine.dispose()


if __name__ == "__main__":
    main()
