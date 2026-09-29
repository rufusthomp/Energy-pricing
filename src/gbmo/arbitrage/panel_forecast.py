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

    python -m gbmo.arbitrage.panel_forecast [--zones ...] [--workers 12]
"""

import argparse
import datetime as dt
import multiprocessing as mp
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sqlalchemy import create_engine, text

from gbmo import config
from gbmo.arbitrage import lp, panel

FEATURES = ["market_hour", "dow", "month", "td_price", "yday_dev", "yday_mean_dev",
            "load_fc", "wind_fc", "solar_fc", "load_rel", "wind_rel", "solar_rel",
            "day_wind_share", "day_solar_share"]

MIN_TRAIN_DAYS = 180
SEED = 20260927

HOURLY_FORECASTS = """
    SELECT p.datetime, l.mw AS load_fc, f.wind_mw AS wind_fc, f.solar_mw AS solar_fc
    FROM entsoe.price p
    JOIN ref.zone z USING (zone_id)
    LEFT JOIN entsoe.load_forecast l USING (zone_id, datetime)
    LEFT JOIN entsoe.vre_forecast  f USING (zone_id, datetime)
    WHERE z.code = :code AND p.datetime >= :start
"""


def hourly_frame(days, forecasts):
    """One row per scored hour with features and target. Days without a TD profile skip."""
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
    return df


def run_zone(args):
    code, specs, database_url = args
    engine = create_engine(database_url)
    start = pd.Timestamp("2018-01-01")
    params = {"code": code, "start": start.date(), "end": panel.LAST_DAY.date()}
    prices = pd.read_sql(text(panel.PRICES), engine, params=params)
    expected = pd.read_sql(text(panel.EXPECTED_HOURS), engine, params=params)
    forecasts = pd.read_sql(text(HOURLY_FORECASTS), engine, params={"code": code, "start": start})
    engine.dispose()

    days = panel.complete_days(prices, expected)
    df = hourly_frame(days, forecasts)

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
        return code, pd.DataFrame(), 0, 0
    scored = pd.concat(predictions, ignore_index=True)

    rows, failures = [], 0
    for day, frame in scored.groupby("delivery_date"):
        if not (panel.FIRST_DAY.date() <= day <= panel.LAST_DAY.date()):
            continue
        actual = frame["price"].to_numpy()
        for spec in specs:
            schedule = lp.solve_day(frame["fc_price"].to_numpy(), spec,
                                    period_hours=panel.PERIOD_HOURS)
            if not schedule.ok:
                failures += 1
                continue
            rows.append({"strategy": "gbm_forecast", "battery": spec.name, "zone": code,
                         "delivery_date": day, **panel.settle(schedule, actual, spec)})
    return code, pd.DataFrame(rows), failures, scored["delivery_date"].nunique()


def main():
    parser = argparse.ArgumentParser(description="Backtest the forecaster operator.")
    parser.add_argument("--zones", nargs="*", default=panel.PANEL_ZONES)
    parser.add_argument("--workers", type=int, default=min(12, mp.cpu_count()))
    args = parser.parse_args()

    url = config.DATABASE_URL
    engine = create_engine(url)
    specs = panel.load_specs(engine)
    started = time.perf_counter()
    frames, failures = [], 0
    with mp.Pool(args.workers) as pool:
        for code, frame, failed, n in pool.imap_unordered(
                run_zone, [(z, specs, url) for z in args.zones]):
            frames.append(frame)
            failures += failed
            print(f"  {code:<8} {n:>5,} forecast days, {len(frame):>6,} results "
                  f"({time.perf_counter() - started:4.0f}s)", flush=True)
    panel.write(engine, pd.concat(frames, ignore_index=True), args.zones, failures)
    engine.dispose()
    print(f"done in {time.perf_counter() - started:.0f}s")


if __name__ == "__main__":
    main()
