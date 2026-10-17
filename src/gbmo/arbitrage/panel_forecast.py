"""The forecaster operator (FC) for the panel: typical day plus a learned correction.

FC nests TD by construction. Its forecast for hour h of day d is the typical-day price
for that market hour plus a gradient-boosted prediction of the day's deviation from it,
learned from information available at gate closure:

    - the TSO day-ahead forecasts of load, wind and solar for each hour of d, and their
      daily totals relative to the typical level of the last 28 days;
    - yesterday's price at the same hour and yesterday's mean, relative to the profile;
    - market hour, weekday and month.

So `FC - TD` is what this model extracts from day-specific fundamentals. It is not the
value of that information itself: a model trained on squared price error need not win
on arbitrage revenue, and this one does not beat TD in four zones. The target is
the deviation from the profile rather than the price level because tree ensembles cannot
extrapolate levels, and the 2022 crisis took prices well outside anything in the early
training data. The shape of the day is what arbitrage earns from anyway.

Expanding window, refitted monthly: every forecast for month M comes from a model trained
only on days before M. The first 180 days of each zone train the first model and are not
scored, and they sit before the panel window, so no scored day is lost. The pre-registered
caveat applies: TSO wind and solar forecasts are due by 18:00 on D-1, after the 12:00
auction, so FC slightly overstates what an operator knew at gate closure.

`--target shape` is the referee's variant: a battery that starts and ends each day empty
earns on the within-day shape and rank order of prices, not their level, so squared error
on the level (the default `deviation` target, `price - td_price`) rewards the model for
effort a flat-empty battery cannot monetise. `shape` trains on the same deviation with
each day's own mean removed from both price and TD, so the target carries only the shape;
TD still supplies the level, since the plan price is always `td_price + prediction`. Same
features, hyperparameters, seed, expanding refit and MIN_TRAIN_DAYS; only the target and
the written strategy name (`gbm_shape`) differ. Written to `model.run` as its own strategy
so the two forecasters sit side by side rather than one overwriting the other.

Alongside the daily_result rows, every scored day's Spearman rank correlation between the
plan prices and actual prices (rho_fc), and between td_price and actual prices (rho_td),
is written to `data/derived/forecast_rank_<strategy>.parquet`. This is a diagnostic on
what the forecaster actually improves (rank order, the thing arbitrage is paid for), not
part of the backtest, so it never touches the database.

    python -m gbmo.arbitrage.panel_forecast [--zones ...] [--workers 12] [--target deviation|shape]
"""

import argparse
import datetime as dt
import multiprocessing as mp
import time

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sqlalchemy import create_engine, text

from gbmo import config
from gbmo.arbitrage import lp, panel

FEATURES = ["market_hour", "dow", "month", "td_price", "yday_dev", "yday_mean_dev",
            "load_fc", "wind_fc", "solar_fc", "load_rel", "wind_rel", "solar_rel",
            "day_wind_share", "day_solar_share"]

MIN_TRAIN_DAYS = 180
SEED = 20260927

STRATEGY_NAMES = {"deviation": "gbm_forecast", "shape": "gbm_shape"}
RANK_DIR = config.DATA_DIR / "derived"

HOURLY_FORECASTS = """
    SELECT p.datetime, l.mw AS load_fc, f.wind_mw AS wind_fc, f.solar_mw AS solar_fc
    FROM entsoe.price p
    JOIN ref.zone z USING (zone_id)
    LEFT JOIN entsoe.load_forecast l USING (zone_id, datetime)
    LEFT JOIN entsoe.vre_forecast  f USING (zone_id, datetime)
    WHERE z.code = :code AND p.datetime >= :start
"""


def hourly_frame(days, forecasts, target="deviation"):
    """One row per scored hour with features and target. Days without a TD profile skip.

    `target="shape"` subtracts each day's own mean from the deviation target, so the model
    is scored and trained on the within-day shape only; `price - td_price` de-meaned by day
    is exactly `(price - day_mean(price)) - (td_price - day_mean(td_price))`.
    """
    rows = []
    for day in sorted(days):
        profile = panel.typical_day_profile(days, day)
        if profile is None:
            continue
        frame = days[day].copy()
        frame["td_price"] = panel.forecast_for(profile, frame)
        ps = panel.persistence_profile(days, day)
        yday = panel.forecast_for(ps, frame) if ps is not None else np.full(len(frame), np.nan)
        frame["yday_dev"] = yday - frame["td_price"]
        frame["yday_mean_dev"] = np.nanmean(yday) - frame["td_price"].mean() if ps is not None else np.nan
        frame["delivery_date"] = day
        rows.append(frame)
    df = pd.concat(rows, ignore_index=True).merge(forecasts, on="datetime", how="left")

    d = pd.to_datetime(df["delivery_date"])
    df["dow"] = d.dt.dayofweek
    df["month"] = d.dt.month
    cols = ["load_fc", "wind_fc", "solar_fc"]
    by_day = df.groupby("delivery_date")
    # A daily share is defined only when the forecast covers every hour of the day, the
    # same rule as the regression treatments; summing over partial hours biases it
    complete = by_day[cols].transform("count").eq(by_day["price"].transform("size"), axis=0)
    daily = by_day[cols].transform("sum").where(complete)
    df["day_wind_share"] = daily["wind_fc"] / daily["load_fc"]
    df["day_solar_share"] = daily["solar_fc"] / daily["load_fc"]
    # Relative to the zone's own level over the previous 28 *calendar* days, so the model
    # learns anomalies rather than a zone's absolute size. closed="left" excludes day d
    # itself; a row-count window would span more than 28 days after any data gap.
    day_index = pd.to_datetime(df["delivery_date"])
    for c in cols:
        daily_mean = by_day[c].mean()
        daily_mean.index = pd.to_datetime(daily_mean.index)
        level = daily_mean.rolling("28D", min_periods=14, closed="left").mean()
        df[c.replace("_fc", "_rel")] = df[c] / day_index.map(level).replace(0, np.nan).to_numpy()
    df["target"] = df["price"] - df["td_price"]
    if target == "shape":
        df["target"] = df["target"] - df.groupby("delivery_date")["target"].transform("mean")
    return df


def run_zone(args):
    code, specs, database_url, target = args
    strategy = STRATEGY_NAMES[target]
    engine = create_engine(database_url)
    start = pd.Timestamp("2018-01-01")
    params = {"code": code, "start": start.date(), "end": panel.LAST_DAY.date()}
    prices = pd.read_sql(text(panel.PRICES), engine, params=params)
    expected = pd.read_sql(text(panel.EXPECTED_HOURS), engine, params=params)
    forecasts = pd.read_sql(text(HOURLY_FORECASTS), engine, params={"code": code, "start": start})
    engine.dispose()

    days = panel.complete_days(prices, expected)
    df = hourly_frame(days, forecasts, target=target)

    months = sorted({(d.year, d.month) for d in df["delivery_date"]
                     if panel.FIRST_DAY.date() <= d <= panel.LAST_DAY.date()})
    predictions = []
    for year, month in months:
        first = dt.date(year, month, 1)
        train = df[df["delivery_date"] < first].dropna(subset=["target"])
        if train["delivery_date"].nunique() < MIN_TRAIN_DAYS:
            continue
        model = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05,
                                              max_leaf_nodes=31, min_samples_leaf=40,
                                              l2_regularization=1.0, random_state=SEED)
        model.fit(train[FEATURES], train["target"])
        test = df[(pd.to_datetime(df["delivery_date"]).dt.year == year)
                  & (pd.to_datetime(df["delivery_date"]).dt.month == month)]
        predictions.append(test.assign(fc_price=test["td_price"] + model.predict(test[FEATURES])))
    if not predictions:
        return code, pd.DataFrame(), pd.DataFrame(), 0, 0
    scored = pd.concat(predictions, ignore_index=True)

    rows, ranks, failures = [], [], 0
    for day, frame in scored.groupby("delivery_date"):
        if not (panel.FIRST_DAY.date() <= day <= panel.LAST_DAY.date()):
            continue
        actual = frame["price"].to_numpy()
        fc_price = frame["fc_price"].to_numpy()
        td_price = frame["td_price"].to_numpy()
        rho_fc = (spearmanr(fc_price, actual).statistic
                  if actual.std() > 0 and fc_price.std() > 0 else np.nan)
        rho_td = (spearmanr(td_price, actual).statistic
                  if actual.std() > 0 and td_price.std() > 0 else np.nan)
        ranks.append({"zone": code, "delivery_date": day, "hours": len(frame),
                      "rho_fc": rho_fc, "rho_td": rho_td})
        for spec in specs:
            schedule = lp.solve_day(fc_price, spec, period_hours=panel.PERIOD_HOURS)
            if not schedule.ok:
                failures += 1
                continue
            rows.append({"strategy": strategy, "battery": spec.name, "zone": code,
                         "delivery_date": day, **panel.settle(schedule, actual, spec)})
    return code, pd.DataFrame(rows), pd.DataFrame(ranks), failures, scored["delivery_date"].nunique()


def main():
    parser = argparse.ArgumentParser(description="Backtest the forecaster operator.")
    parser.add_argument("--zones", nargs="*", default=panel.PANEL_ZONES)
    parser.add_argument("--workers", type=int, default=min(12, mp.cpu_count()))
    parser.add_argument("--target", choices=list(STRATEGY_NAMES), default="deviation",
                        help="deviation (default): price - td_price. shape: the within-day "
                             "shape only, each day's own mean removed from the target.")
    args = parser.parse_args()
    strategy = STRATEGY_NAMES[args.target]

    url = config.DATABASE_URL
    engine = create_engine(url)
    specs = panel.load_specs(engine)
    started = time.perf_counter()
    frames, rank_frames, failures = [], [], 0
    with mp.Pool(args.workers) as pool:
        for code, frame, ranks, failed, n in pool.imap_unordered(
                run_zone, [(z, specs, url, args.target) for z in args.zones]):
            frames.append(frame)
            rank_frames.append(ranks)
            failures += failed
            print(f"  {code:<8} {n:>5,} forecast days, {len(frame):>6,} results "
                  f"({time.perf_counter() - started:4.0f}s)", flush=True)
    panel.write(engine, pd.concat(frames, ignore_index=True), args.zones, failures)
    engine.dispose()

    RANK_DIR.mkdir(parents=True, exist_ok=True)
    rank_path = RANK_DIR / f"forecast_rank_{strategy}.parquet"
    pd.concat(rank_frames, ignore_index=True).to_parquet(rank_path, index=False)
    print(f"rank correlations -> {rank_path}")
    print(f"done in {time.perf_counter() - started:.0f}s")


if __name__ == "__main__":
    main()
