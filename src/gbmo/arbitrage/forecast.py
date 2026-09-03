"""Day-ahead price forecasting, and the information variants that bound it.

The controller built on this runs the *same* MILP as the ceiling, on forecast prices
instead of actual ones, and is then scored against actual prices. Same optimiser, same
daily boundaries, same battery. The only thing that differs is the price vector, so any
gap between this and the ceiling is forecast error and nothing else.

**Target is within-day shape**, not price. Dispatch depends on the spread between periods,
not the level: adding a constant to every price in a day leaves the schedule almost
unchanged (almost, not exactly, because the battery is a net consumer of about 16 MWh a
day, so a higher level makes round-trip losses dearer). Net demand explains price *level*
at 0.27 and price *shape* at 0.48, so forecasting shape roughly doubles the available
signal. The level is added back from the previous day's mean, which the schedule is
barely sensitive to.

**Three information variants**, which is the point of the module:

    price      lagged prices only. What a forecaster with no physical data can do.
    physical   plus lagged net demand. What is genuinely knowable at the day boundary.
    oracle     plus *actual* net demand for the day being forecast. Not achievable, and
               not meant to be: it isolates how much of the capture loss is price-model
               error and how much is the irreducible difficulty of predicting weather.

If the oracle recovers most of the ceiling, the capture loss is a weather-forecasting
problem. If even the oracle falls short, price formation has become harder for reasons
beyond renewable output, which would be a different and more interesting finding.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

PERIODS_PER_DAY = 48

# The ablation. Each variant is the one before it plus a defined piece of information,
# so the difference between two rows is the value of exactly that information.
WEATHER_FEATURES = ["wind_shape", "wind_cubed_shape", "solar_shape", "temp_shape"]

VARIANTS = {
    "price": [],
    "physical": ["nd_shape_lag1", "nd_shape_lag7"],
    # Reanalysis weather for the day being forecast. Mildly optimistic rather than an
    # oracle: unlike day-ahead prices, day-ahead weather is genuinely forecastable at
    # national aggregate, so this approximates what an operator with a met feed holds.
    "weather": WEATHER_FEATURES,
    "physical_weather": ["nd_shape_lag1", "nd_shape_lag7", *WEATHER_FEATURES],
    # Actual net demand for the day. Not achievable; the upper bound on what physical
    # information can buy.
    "oracle": ["nd_shape_lag1", "nd_shape_lag7", "nd_shape_actual"],
}

BASE_FEATURES = [
    "period",           # 0-47, the within-day position
    "shape_lag1",       # same period yesterday
    "shape_lag7",       # same period last week
    "prev_day_mean",    # level context, and a proxy for the gas regime
    "prev_day_sd",      # how volatile the shape was yesterday
    "dow",
    "month",
]

QUERY = """
    SELECT sp.date, sp.datetime, p.price, d.tsd,
           sum(g.mw) FILTER (WHERE f.name IN ('WIND','WIND_EMB','SOLAR')) AS vre_mw
    FROM settlement_period sp
    JOIN price p      ON p.time_id = sp.time_id
    JOIN demand d     ON d.time_id = sp.time_id
    JOIN generation g ON g.time_id = sp.time_id
    JOIN fuel f       ON f.fuel_id = g.fuel_id
    WHERE sp.year >= 2018
    GROUP BY sp.date, sp.datetime, p.price, d.tsd
    ORDER BY sp.datetime
"""

# Weather is hourly, settlement periods are half-hourly, so each period takes the value
# of the hour containing it. Wind is averaged over the three offshore and Scottish sites
# because GB wind output is a national aggregate, not a point measurement; solar is taken
# from the south, where the fleet is; temperature from London, as the demand proxy.
WEATHER_QUERY = """
    SELECT datetime,
           avg(value) FILTER (WHERE variable = 'wind_speed_100m'
                              AND location IN ('scotland','north_sea','irish_sea')) AS wind,
           avg(value) FILTER (WHERE variable = 'shortwave_radiation'
                              AND location = 'south')  AS solar,
           avg(value) FILTER (WHERE variable = 'temperature_2m'
                              AND location = 'london') AS temp
    FROM weather
    GROUP BY datetime
    ORDER BY datetime
"""


def build_frame(engine):
    """One row per (day, period) with everything the models need.

    Only complete 48-period days survive: a partial day cannot be optimised against and
    would put an inconsistent denominator into the comparison.
    """
    df = pd.read_sql(QUERY, engine)
    df["date"] = pd.to_datetime(df["date"])
    df["period"] = df.groupby("date").cumcount()

    complete = df.groupby("date")["period"].transform("size") == PERIODS_PER_DAY
    df = df[complete].copy()

    # Hourly weather onto half-hourly periods
    wx = pd.read_sql(WEATHER_QUERY, engine)
    wx["datetime"] = pd.to_datetime(wx["datetime"])
    df["hour"] = pd.to_datetime(df["datetime"]).dt.floor("h")
    df = df.merge(wx.rename(columns={"datetime": "hour"}), on="hour", how="left")

    # Turbine output rises roughly with the cube of wind speed between cut-in and rated,
    # so the cube is the physically motivated term; the raw speed is kept as well because
    # the relationship flattens above rated and stops at cut-out.
    df["wind_cubed"] = (df["wind"] / 10.0) ** 3

    df["net_demand"] = df["tsd"] - df["vre_mw"]
    df["day_mean"] = df.groupby("date")["price"].transform("mean")
    df["shape"] = df["price"] - df["day_mean"]
    df["nd_shape_actual"] = df["net_demand"] - df.groupby("date")["net_demand"].transform("mean")

    # Weather enters as within-day shape too, since that is what the target is
    for raw, name in [("wind", "wind_shape"), ("wind_cubed", "wind_cubed_shape"),
                      ("solar", "solar_shape"), ("temp", "temp_shape")]:
        df[name] = df[raw] - df.groupby("date")[raw].transform("mean")

    # Lags are taken on the calendar, not on row position, so a gap in the price data
    # produces a missing feature rather than a silently wrong one.
    for lag in (1, 7):
        shifted = df[["date", "period", "shape", "nd_shape_actual"]].copy()
        shifted["date"] = shifted["date"] + pd.Timedelta(days=lag)
        shifted = shifted.rename(columns={
            "shape": f"shape_lag{lag}", "nd_shape_actual": f"nd_shape_lag{lag}"})
        df = df.merge(shifted, on=["date", "period"], how="left")

    prev = df.groupby("date")["shape"].agg(["mean", "std"]).rename(
        columns={"mean": "_m", "std": "prev_day_sd"})
    prev["prev_day_mean"] = df.groupby("date")["price"].mean()
    prev.index = prev.index + pd.Timedelta(days=1)
    df = df.merge(prev[["prev_day_sd", "prev_day_mean"]], left_on="date",
                  right_index=True, how="left")

    df["dow"] = df["date"].dt.dayofweek
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year

    needed = (BASE_FEATURES + WEATHER_FEATURES
              + ["shape", "nd_shape_actual", "nd_shape_lag1", "nd_shape_lag7"])
    df = df.dropna(subset=[c for c in needed if c in df.columns])
    return df.sort_values(["date", "period"]).reset_index(drop=True)


def features_for(variant):
    return BASE_FEATURES + VARIANTS[variant]


def fit_predict_expanding(df, variant, first_test_year=2019, seed=0):
    """Out-of-sample predictions for every year, refitting as history accumulates.

    For each test year, train on everything strictly before it. That is what an operator
    could actually have done, and it avoids training on the gas crisis to predict years
    that preceded it. A single fixed split would either waste the recent data or leak
    the future into the past.
    """
    cols = features_for(variant)
    out = []

    for year in sorted(df.loc[df.year >= first_test_year, "year"].unique()):
        train = df[df.year < year]
        test = df[df.year == year]
        if train.empty or test.empty:
            continue

        model = HistGradientBoostingRegressor(
            max_iter=400, learning_rate=0.06, max_depth=6,
            l2_regularization=1.0, random_state=seed,
        )
        model.fit(train[cols], train["shape"])

        predicted = test[["date", "period", "shape", "day_mean", "price",
                          "prev_day_mean", "year"]].copy()
        predicted["shape_hat"] = model.predict(test[cols])
        predicted["variant"] = variant
        out.append(predicted)

    result = pd.concat(out, ignore_index=True)
    # Reconstruct a price from the forecast shape. The level barely moves the schedule,
    # so yesterday's mean is a sufficient stand-in and keeps the forecast honest about
    # what was knowable.
    result["price_hat"] = result["shape_hat"] + result["prev_day_mean"]
    return result


def accuracy(predictions):
    """Shape MAE and RMSE by year, which is the forecast-quality view."""
    err = predictions["shape_hat"] - predictions["shape"]
    frame = predictions.assign(err=err, abs_err=err.abs(), sq_err=err**2)
    return frame.groupby(["variant", "year"]).agg(
        mae=("abs_err", "mean"),
        rmse=("sq_err", lambda s: float(np.sqrt(s.mean()))),
        shape_sd=("shape", "std"),
    ).reset_index()
