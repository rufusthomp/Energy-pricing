"""Zone-day weather instruments for the panel, from ERA5 reanalysis in `weather.*`.

The paper's treatments are TSO forecast penetration: forecast output over forecast load.
They can move for reasons other than weather (a load forecast that falls on sunny days, a
forecast that is updated after the auction or netted of curtailment at negative prices).
Realised weather has none of those channels, so it serves as an instrument:

- `wind_cf`: the mean, over a zone's wind points, of a stylised turbine power curve applied
  to 100 m wind speed, averaged over the delivery day's hours. Cut-in 3 m/s, rated 12 m/s,
  cut-out 25 m/s, cubic in between. It is a capacity factor for a notional turbine, not
  the zone's fleet.
- `solar_kwh`: the mean, over a zone's solar points, of the day's shortwave radiation
  in kWh/m2.

Points are weighted equally within a zone. How the points were chosen is recorded in
`weather.point.description`.

    python -m gbmo.analysis.weather_days      # -> data/derived/weather_days.parquet
"""

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from gbmo import config

WEATHER_PATH = config.REPO_ROOT / "data" / "derived" / "weather_days.parquet"
CUT_IN, RATED, CUT_OUT = 3.0, 12.0, 25.0   # m/s

HOURLY = """
    SELECT z.code AS zone, c.delivery_date, p.role, p.point,
           o.wind_speed_100m, o.shortwave_radiation
    FROM weather.observation o
    JOIN weather.point p USING (point_id)
    JOIN ref.zone z ON z.zone_id = p.zone_id
    JOIN entsoe.calendar c ON c.zone_id = p.zone_id AND c.datetime = o.datetime
"""


def power_curve(speed_kmh):
    """Capacity factor of a notional turbine at a 100 m wind speed given in km/h."""
    v = np.asarray(speed_kmh, dtype=float) / 3.6
    cf = (v ** 3 - CUT_IN ** 3) / (RATED ** 3 - CUT_IN ** 3)
    cf = np.where(v < CUT_IN, 0.0, np.where(v >= RATED, 1.0, cf))
    return np.where(v >= CUT_OUT, 0.0, cf)


def build(engine):
    hourly = pd.read_sql(text(HOURLY), engine)
    hourly["cf"] = power_curve(hourly["wind_speed_100m"])
    wind = (hourly[hourly["role"].isin(["wind", "both"])]
            .groupby(["zone", "delivery_date", "point"])["cf"].mean()
            .groupby(["zone", "delivery_date"]).mean().rename("wind_cf"))
    solar = (hourly[hourly["role"].isin(["solar", "both"])]
             .groupby(["zone", "delivery_date", "point"])["shortwave_radiation"].sum()
             .div(1000).groupby(["zone", "delivery_date"]).mean().rename("solar_kwh"))
    out = pd.concat([wind, solar], axis=1).reset_index()
    out["delivery_date"] = pd.to_datetime(out["delivery_date"]).dt.date
    return out


def main():
    engine = create_engine(config.DATABASE_URL)
    out = build(engine)
    engine.dispose()
    WEATHER_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(WEATHER_PATH, index=False)
    print(f"{len(out):,} zone-days, {out['zone'].nunique()} zones -> {WEATHER_PATH}")
    print(out.groupby("zone")[["wind_cf", "solar_kwh"]].mean().round(3).to_string())


if __name__ == "__main__":
    main()
