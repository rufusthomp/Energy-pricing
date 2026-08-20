"""Source and clean the two commodity inputs that were missing for dynamic SRMC (v2).

Writes cleaned CSVs into ../data/raw/commodity/ alongside the ones cleaned by hand on
2026-07-15. Run from src/. Re-running overwrites; each output is a pure function of its
source, so this is safe to repeat.

1. Coal p/kWh — extracted from the QEP 3.2.1 workbook already downloaded for gas. Same
   sheet, same rows, different column; the hand-cleaned pass only took the gas column.
2. EUR->GBP — ECB reference rates via the Frankfurter API (free, no key). Needed because
   the EUA series is denominated in EUR and neither ICAP export carries a GBP/EUR rate
   before the UK ETS launched in May 2021.
"""

import pandas as pd
import requests

COMMODITY_DIR = r"..\data\raw\commodity"

QUARTER_TO_NUM = {"Jan to Mar": 1, "Apr to Jun": 2, "Jul to Sep": 3, "Oct to Dec": 4}
QUARTER_START_MONTH = {1: 1, 2: 4, 3: 7, 4: 10}


def clean_coal():
    """QEP 3.2.1 -> coal_price_qep_321.csv, matching the gas CSV's column layout."""
    df = pd.read_excel(
        rf"{COMMODITY_DIR}\qep_3_2_1_fuel_prices_power_producers.xlsx",
        sheet_name="3.2.1",
        header=10,
    )
    # Positional, not by name: the header text carries a mojibake pound sign and
    # footnote markers that are not worth matching on.
    df = df.iloc[:, [0, 1, 3]]
    df.columns = ["year", "quarter", "coal_pence_per_kwh_gcv"]

    # Drop the note/blank rows that trail the data block
    df = df[pd.to_numeric(df["year"], errors="coerce").notna()]
    df["year"] = df["year"].astype(int)
    df["quarter"] = df["quarter"].map(QUARTER_TO_NUM)
    df = df.dropna(subset=["quarter"])
    df["quarter"] = df["quarter"].astype(int)

    # '..' marks a suppressed/absent price (no coal purchased from 2025 onward)
    df["coal_pence_per_kwh_gcv"] = pd.to_numeric(
        df["coal_pence_per_kwh_gcv"], errors="coerce"
    )
    df = df.dropna(subset=["coal_pence_per_kwh_gcv"])

    df["quarter_start"] = pd.to_datetime(
        dict(year=df["year"], month=df["quarter"].map(QUARTER_START_MONTH), day=1)
    ).dt.strftime("%Y-%m-%d")

    df = df[["year", "quarter", "quarter_start", "coal_pence_per_kwh_gcv"]]
    df.to_csv(rf"{COMMODITY_DIR}\coal_price_qep_321.csv", index=False)
    print(f"coal: {len(df)} quarters, {df['year'].min()}-{df['year'].max()}")


def fetch_fx(start="2009-01-01", end="2026-12-31"):
    """ECB daily EUR->GBP -> fx_eur_gbp_monthly_ecb.csv (monthly mean of daily rates)."""
    r = requests.get(
        f"https://api.frankfurter.dev/v1/{start}..{end}",
        params={"base": "EUR", "symbols": "GBP"},
        timeout=60,
    )
    r.raise_for_status()
    rates = r.json()["rates"]

    fx = pd.DataFrame(
        [(date, v["GBP"]) for date, v in rates.items()], columns=["date", "gbp_per_eur"]
    )
    fx["date"] = pd.to_datetime(fx["date"])
    fx = fx.sort_values("date")

    monthly = (
        fx.set_index("date")["gbp_per_eur"]
        .resample("MS")
        .mean()
        .reset_index()
        .rename(columns={"date": "month"})
    )
    monthly["month"] = monthly["month"].dt.strftime("%Y-%m")
    # The API returns the last business day before `start`, which lands a one-observation
    # month at the front. Drop it rather than publish a monthly mean built from one day.
    monthly = monthly[monthly["month"] >= start[:7]]
    monthly.to_csv(rf"{COMMODITY_DIR}\fx_eur_gbp_monthly_ecb.csv", index=False)
    print(
        f"fx: {len(monthly)} months, {monthly['month'].min()}-{monthly['month'].max()}"
        f" (daily obs: {len(fx)})"
    )


if __name__ == "__main__":
    clean_coal()
    fetch_fx()
