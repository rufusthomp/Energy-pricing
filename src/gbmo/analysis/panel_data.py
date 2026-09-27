"""The zone-day analysis frame for the wind/solar composition study.

One row per zone and CET delivery day, joining what the operators earned
(`model.daily_result`) to what the TSOs forecast the day before (`entsoe.vre_forecast`,
`entsoe.load_forecast`), plus the price-shape mechanism variables. Every variable is
defined in docs/preregistration.md, and this module is the only place they are computed.

Derived, so it is written to `data/derived/` (gitignored) and never to the database.

    python -m gbmo.analysis.panel_data
"""

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from gbmo import config
from gbmo.arbitrage import panel

DERIVED_DIR = config.DATA_DIR / "derived"
FRAME_PATH = DERIVED_DIR / "panel_days.parquet"

STRATEGY_COLUMN = {"lp_perfect_foresight": "v_pf", "typical_day": "v_td",
                   "persistence": "v_ps", "gbm_forecast": "v_fc"}

# Revenue per MW. The stored runs are 50 MW batteries; a price-taker's optimum scales
# linearly in size, so dividing by the rating is exact rather than an approximation.
REVENUE = """
    SELECT s.name AS strategy, b.name AS battery, z.code AS zone, d.delivery_date,
           d.revenue / b.power_mw AS revenue_per_mw
    FROM model.daily_result d
    JOIN model.run r USING (run_id)
    JOIN model.strategy s USING (strategy_id)
    JOIN model.battery_spec b USING (battery_id)
    JOIN ref.zone z USING (zone_id)
    WHERE r.price_source = 'entsoe_day_ahead'
"""

# Daily sums of the day-ahead forecasts, and of realised wind for the placebo. The hour
# counts let the frame drop any day whose forecasts do not cover all its hours.
FORECASTS = """
    SELECT z.code AS zone, c.delivery_date,
           count(*)          AS hours,
           count(l.mw)       AS load_hours,
           count(f.wind_mw)  AS wind_hours,
           count(f.solar_mw) AS solar_hours,
           count(g.wind_mw)  AS wind_actual_hours,
           sum(l.mw)         AS load_fc_mwh,
           sum(f.wind_mw)    AS wind_fc_mwh,
           sum(f.solar_mw)   AS solar_fc_mwh,
           sum(g.wind_mw)    AS wind_actual_mwh
    FROM entsoe.calendar c
    JOIN ref.zone z USING (zone_id)
    LEFT JOIN entsoe.load_forecast l USING (zone_id, datetime)
    LEFT JOIN entsoe.vre_forecast  f USING (zone_id, datetime)
    LEFT JOIN entsoe.generation    g USING (zone_id, datetime)
    WHERE z.code = ANY(:zones) AND c.delivery_date BETWEEN :start AND :end
    GROUP BY z.code, c.delivery_date
"""


def typical_day_profiles(days):
    """{day: profile} for every day, identical to `panel.typical_day_profile` but vectorised.

    The panel operator computes each profile by concatenating 28 frames and grouping, which
    is fine once per backtest and far too slow when repeated for every zone-day here. Rolling
    sums and counts by market hour give the same mean exactly, including clock-change days
    (a 25-hour day contributes both hour-2 prices to the sum and 2 to the count).
    """
    dates = pd.date_range(min(days), max(days)).date
    hours = range(24)
    sums = pd.DataFrame(0.0, index=dates, columns=hours)
    counts = pd.DataFrame(0.0, index=dates, columns=hours)
    complete = pd.Series(0.0, index=dates)
    for day, frame in days.items():
        g = frame.groupby("market_hour")["price"].agg(["sum", "count"])
        sums.loc[day, g.index] = g["sum"].to_numpy()
        counts.loc[day, g.index] = g["count"].to_numpy()
        complete[day] = 1.0
    window = panel.TD_WINDOW_DAYS
    s = sums.rolling(window, min_periods=1).sum().shift(1)
    c = counts.rolling(window, min_periods=1).sum().shift(1)
    n = complete.rolling(window, min_periods=1).sum().shift(1)
    profile = s / c.replace(0, np.nan)
    ok = n >= panel.TD_MIN_DAYS
    return {d: profile.loc[d].dropna() for d in dates if ok.get(d, False)}


def shape_variables(days):
    """Novelty and spread for every day with a typical-day profile.

    novelty = 1 - corr(day's prices, typical-day profile mapped onto its hours). Zero means
    the day had exactly the shape of the last four weeks; one means none of it.
    """
    profiles = typical_day_profiles(days)
    rows = []
    for day, frame in days.items():
        if not (panel.FIRST_DAY.date() <= day <= panel.LAST_DAY.date()):
            continue
        actual = frame["price"].to_numpy()
        profile = profiles.get(day)
        spread = float(actual.max() - actual.min())
        novelty = np.nan
        if profile is not None and actual.std() > 0:
            expected = panel.forecast_for(profile, frame)
            if expected.std() > 0:
                novelty = 1.0 - float(np.corrcoef(actual, expected)[0, 1])
        rows.append({"delivery_date": day, "spread": spread, "novelty": novelty,
                     "mean_price": float(actual.mean())})
    return pd.DataFrame(rows)


def ratio_keep(df, duration, pct):
    """Days on which a capture share is defined and above the pre-registered floor.

    A share of zero value is undefined, not zero: NO_2 has 609 days with perfectly flat
    prices and V* = 0. So the ratio needs V* > 0, and the floor is the zone's `pct`
    quantile among days with V* > 0. Only NO_2 has zero-value days, so only its floor is
    affected by computing it among positive days.
    """
    pf = df[f"v_pf_{duration}"]
    positive = pf.where(pf > 0)
    floor = positive.groupby(df["zone"]).transform(lambda x: x.quantile(pct))
    return (pf > 0) & (pf >= floor)


def build(database_url=None):
    engine = create_engine(database_url or config.DATABASE_URL)
    zones = panel.PANEL_ZONES
    params = {"zones": zones, "start": panel.FIRST_DAY.date(), "end": panel.LAST_DAY.date()}

    revenue = pd.read_sql(text(REVENUE), engine)
    revenue["col"] = revenue["strategy"].map(STRATEGY_COLUMN) + "_" + revenue["battery"].str[:2]
    wide = revenue.pivot_table(index=["zone", "delivery_date"], columns="col",
                               values="revenue_per_mw").reset_index()

    fc = pd.read_sql(text(FORECASTS), engine, params=params)

    shapes = []
    for code in zones:
        p = {"code": code, "start": (panel.FIRST_DAY - pd.Timedelta(days=40)).date(),
             "end": panel.LAST_DAY.date()}
        prices = pd.read_sql(text(panel.PRICES), engine, params=p)
        expected = pd.read_sql(text(panel.EXPECTED_HOURS), engine, params=p)
        s = shape_variables(panel.complete_days(prices, expected))
        s["zone"] = code
        shapes.append(s)
    shape = pd.concat(shapes, ignore_index=True)
    engine.dispose()

    df = wide.merge(fc, on=["zone", "delivery_date"], how="left") \
             .merge(shape, on=["zone", "delivery_date"], how="left")

    # A penetration is only defined when the forecast covers every hour of the day, and when
    # the load forecast is plausible: within 50-200% of the zone's median for that month.
    # The rule flags 11 days, all reporting errors (EE load forecasts of 0 to 49% of normal,
    # one GR day at 3%). Relative to the same month so seasonal extremes are never flagged.
    month_key = df["zone"] + pd.to_datetime(df["delivery_date"]).dt.strftime("%Y-%m")
    load_ratio = df["load_fc_mwh"] / df.groupby(month_key)["load_fc_mwh"].transform("median")
    load_ok = load_ratio.between(0.5, 2.0)
    full = lambda col: (df[col] == df["hours"]) & load_ok  # noqa: E731
    df["wind_pen"] = np.where(full("wind_hours") & full("load_hours"),
                              100 * df["wind_fc_mwh"] / df["load_fc_mwh"], np.nan)
    df["solar_pen"] = np.where(full("solar_hours") & full("load_hours"),
                               100 * df["solar_fc_mwh"] / df["load_fc_mwh"], np.nan)
    # Placebo: the part of wind the auction could not have known when it cleared
    df["wind_error"] = np.where(full("wind_actual_hours") & full("wind_hours") & full("load_hours"),
                                100 * (df["wind_actual_mwh"] - df["wind_fc_mwh"]) / df["load_fc_mwh"],
                                np.nan)

    date = pd.to_datetime(df["delivery_date"])
    df["year"] = date.dt.year
    df["month"] = date.dt.month
    df["zone_year"] = df["zone"] + "_" + df["year"].astype(str)
    df["zone_month"] = df["zone"] + "_" + df["month"].astype(str)
    df["date"] = date.dt.strftime("%Y-%m-%d")
    df["k_wind"] = df.groupby("zone_year")["wind_pen"].transform("mean")

    for d in ("1h", "2h", "4h"):
        pf = df.get(f"v_pf_{d}")
        if pf is None:
            continue
        df[f"log_v_pf_{d}"] = np.log(pf.where(pf > 0))
        keep = ratio_keep(df, d, 0.05)
        for op in ("td", "ps", "fc"):
            col = f"v_{op}_{d}"
            if col in df:
                df[f"cap_{op}_{d}"] = np.where(keep, 100 * df[col] / pf, np.nan)
    return df


def main():
    df = build()
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(FRAME_PATH, index=False)
    est = df.dropna(subset=["wind_pen", "solar_pen", "cap_td_2h"])
    print(f"{len(df):,} zone-days, {df['zone'].nunique()} zones -> {FRAME_PATH}")
    print(f"estimation sample (both forecasts, ratio defined): {len(est):,} zone-days, "
          f"{est['zone'].nunique()} zones")


if __name__ == "__main__":
    main()
