"""Pure transforms used by the loaders.

Nothing here touches the database or the network, so it is all directly testable.
The three grain converters exist because the commodity series arrive on three
different grains (quarterly, daily, monthly) and have to be restated onto the one
grain they can share, which is monthly.
"""

import pandas as pd

from gbmo.config import FIRST_YEAR

MONTH_TO_SEASON = {
    12: "winter", 1: "winter", 2: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "autumn", 10: "autumn", 11: "autumn",
}

# Carbon Price Support: a fixed statutory schedule, not a dataset. Financial years run
# from 1 April, and it is £0 before April 2013. Frozen at £18/tCO2 since April 2016 —
# that freeze, not the allowance price, is what kept coal uneconomic through the 2010s.
CPS_SCHEDULE = [(2013, 4.94), (2014, 9.55), (2015, 18.08), (2016, 18.00)]


def cps_rate(year, month):
    """The CPS top-up in GBP/tCO2 for a calendar month, on financial-year boundaries."""
    financial_year = year if month >= 4 else year - 1
    rate = 0.0
    for start_year, value in CPS_SCHEDULE:
        if financial_year >= start_year:
            rate = value
    return rate


def quarterly_to_monthly(path, value_col):
    """QEP is quarterly; repeat each quarter's price across its three months."""
    q = pd.read_csv(path)
    q = q.loc[q["year"] >= FIRST_YEAR, ["year", "quarter", value_col]].reset_index(drop=True)
    q = q.loc[q.index.repeat(3)].copy()
    q["month"] = (q["quarter"] - 1) * 3 + 1 + q.groupby(level=0).cumcount()
    return q.rename(columns={value_col: "price"})[["year", "month", "price"]]


def daily_to_monthly(path, value_col):
    """Daily end-of-day series -> mean over each calendar month."""
    d = pd.read_csv(path, parse_dates=["date"])
    d = d[d["date"].dt.year >= FIRST_YEAR].copy()
    d["year"] = d["date"].dt.year
    d["month"] = d["date"].dt.month
    d = d.groupby(["year", "month"], as_index=False)[value_col].mean()
    return d.rename(columns={value_col: "price"})


def year_month_to_monthly(path, month_col, value_col):
    """A series already published monthly, keyed 'YYYY-MM'."""
    m = pd.read_csv(path)
    parsed = pd.to_datetime(m[month_col])
    m["year"] = parsed.dt.year
    m["month"] = parsed.dt.month
    m = m[m["year"] >= FIRST_YEAR]
    return m.rename(columns={value_col: "price"})[["year", "month", "price"]]


def build_time_dimension(datetimes):
    """Calendar attributes for each distinct settlement timestamp.

    Stored rather than derived at query time because a calendar is immutable: there
    is no update-anomaly risk, and it defines `season` once instead of in every query.
    """
    time_df = pd.DataFrame({"datetime": pd.Series(datetimes).drop_duplicates()})
    parsed = pd.to_datetime(time_df["datetime"])

    time_df["date"] = parsed.dt.strftime("%Y-%m-%d")
    time_df["month"] = parsed.dt.month
    time_df["year"] = parsed.dt.year
    time_df["season"] = time_df["month"].map(MONTH_TO_SEASON)
    return time_df


def collapse_price_providers(price_df):
    """Volume-weight the two MID providers (APX/N2EX) into one price per period.

    Elexon publishes a Market Index Price per provider. A straight mean would weight
    a thin provider equally with a deep one, so the collapse is volume-weighted.
    """
    price_df = price_df.copy()
    price_df["pv"] = price_df["price"] * price_df["volume"]
    grouped = price_df.groupby("startTime", as_index=False)[["pv", "volume"]].sum()
    grouped["price"] = grouped["pv"] / grouped["volume"]
    return grouped.dropna(subset=["price"])
