"""Tests for the pure transforms.

These cover the logic that is easy to get quietly wrong and expensive to notice later:
the statutory CPS financial-year boundary, the three grain conversions, and the
volume weighting of the two MID providers.
"""

from datetime import date

import pandas as pd
import pytest

from gbmo.ingest import transform


class TestCpsRate:
    """Carbon Price Support runs on financial years starting 1 April, not calendar years."""

    def test_zero_before_the_schedule_starts(self):
        assert transform.cps_rate(2009, 1) == 0.0
        assert transform.cps_rate(2012, 12) == 0.0

    def test_march_2013_is_still_zero(self):
        # FY2012: the schedule starts in April 2013, so the three months before it are £0
        assert transform.cps_rate(2013, 3) == 0.0

    def test_april_2013_is_the_first_charged_month(self):
        assert transform.cps_rate(2013, 4) == pytest.approx(4.94)

    def test_january_falls_into_the_previous_financial_year(self):
        # Jan 2014 is FY2013, so it carries the 2013 rate and not the 2014 one
        assert transform.cps_rate(2014, 1) == pytest.approx(4.94)
        assert transform.cps_rate(2014, 4) == pytest.approx(9.55)

    def test_frozen_at_eighteen_pounds_after_2016(self):
        # The freeze, not the allowance price, is what kept coal uneconomic
        assert transform.cps_rate(2016, 4) == pytest.approx(18.00)
        assert transform.cps_rate(2020, 7) == pytest.approx(18.00)
        assert transform.cps_rate(2026, 1) == pytest.approx(18.00)


class TestQuarterlyToMonthly:
    def test_each_quarter_expands_to_its_three_months(self, tmp_path):
        path = tmp_path / "q.csv"
        pd.DataFrame(
            {"year": [2020, 2020], "quarter": [1, 4], "val": [10.0, 40.0]}
        ).to_csv(path, index=False)

        out = transform.quarterly_to_monthly(path, "val")

        assert list(out.columns) == ["year", "month", "price"]
        assert sorted(out.loc[out["price"] == 10.0, "month"]) == [1, 2, 3]
        assert sorted(out.loc[out["price"] == 40.0, "month"]) == [10, 11, 12]
        assert len(out) == 6

    def test_years_before_the_first_modelled_year_are_dropped(self, tmp_path):
        path = tmp_path / "q.csv"
        pd.DataFrame(
            {"year": [2008, 2009], "quarter": [1, 1], "val": [1.0, 2.0]}
        ).to_csv(path, index=False)

        out = transform.quarterly_to_monthly(path, "val")

        assert set(out["year"]) == {2009}


class TestDailyToMonthly:
    def test_takes_the_mean_over_the_calendar_month(self, tmp_path):
        path = tmp_path / "d.csv"
        pd.DataFrame(
            {
                "date": ["2021-05-01", "2021-05-31", "2021-06-15"],
                "price_gbp": [10.0, 20.0, 99.0],
            }
        ).to_csv(path, index=False)

        out = transform.daily_to_monthly(path, "price_gbp")

        may = out[(out["year"] == 2021) & (out["month"] == 5)]["price"].iloc[0]
        assert may == pytest.approx(15.0)
        assert len(out) == 2

    def test_filters_on_year(self, tmp_path):
        path = tmp_path / "d.csv"
        pd.DataFrame(
            {"date": ["2008-01-01", "2009-01-01"], "price_gbp": [1.0, 2.0]}
        ).to_csv(path, index=False)

        out = transform.daily_to_monthly(path, "price_gbp")

        assert set(out["year"]) == {2009}


class TestYearMonthToMonthly:
    def test_parses_a_yyyy_mm_key(self, tmp_path):
        path = tmp_path / "m.csv"
        pd.DataFrame(
            {"month": ["2019-03", "2019-04"], "sap": [1.5, 2.5]}
        ).to_csv(path, index=False)

        out = transform.year_month_to_monthly(path, "month", "sap")

        assert list(out.columns) == ["year", "month", "price"]
        assert out["year"].tolist() == [2019, 2019]
        assert out["month"].tolist() == [3, 4]


class TestBuildTimeDimension:
    def test_deduplicates_timestamps(self):
        out = transform.build_time_dimension(
            ["2020-01-01T00:00:00", "2020-01-01T00:00:00", "2020-01-01T00:30:00"]
        )
        assert len(out) == 2

    def test_maps_months_to_seasons(self):
        out = transform.build_time_dimension(
            ["2020-12-01T00:00:00", "2020-06-01T00:00:00", "2020-03-01T00:00:00"]
        )
        seasons = dict(zip(out["month"], out["season"]))
        assert seasons[12] == "winter"
        assert seasons[6] == "summer"
        assert seasons[3] == "spring"

    def test_emits_real_temporal_types_not_strings(self):
        # Postgres TIMESTAMP and DATE columns need real temporal values. The SQLite
        # build stored ISO strings, where sorting worked by luck and date arithmetic
        # did not work at all.
        out = transform.build_time_dimension(["2020-06-01T13:30:00"])

        assert pd.api.types.is_datetime64_any_dtype(out["datetime"])
        assert isinstance(out["date"].iloc[0], date)
        assert out["date"].iloc[0] == date(2020, 6, 1)


class TestSettlementPeriodToUtc:
    """GB settlement periods are local-clock; generation and price feeds are UTC."""

    @staticmethod
    def convert(date_str, period):
        return transform.settlement_period_to_utc(
            pd.Series([date_str]), pd.Series([period])
        ).iloc[0]

    def test_gmt_winter_is_unchanged(self):
        # Local time equals UTC in winter, so period 1 stays at midnight
        assert self.convert("2023-01-15", 1) == pd.Timestamp("2023-01-15 00:00")

    def test_bst_summer_shifts_back_an_hour(self):
        # The bug this replaces: period 1 is 23:00Z the previous day, not 00:00
        assert self.convert("2023-07-15", 1) == pd.Timestamp("2023-07-14 23:00")
        assert self.convert("2023-07-15", 24) == pd.Timestamp("2023-07-15 10:30")

    def test_spring_forward_day_has_46_periods_covering_23_hours(self):
        # 2023-03-26: clocks go forward, so the local day is an hour short
        first = self.convert("2023-03-26", 1)
        last = self.convert("2023-03-26", 46)
        assert first == pd.Timestamp("2023-03-26 00:00")
        assert last == pd.Timestamp("2023-03-26 22:30")
        assert (last - first) == pd.Timedelta(hours=22, minutes=30)

    def test_fall_back_day_has_50_periods_covering_25_hours(self):
        # 2023-10-29: clocks go back, so the local day gains an hour. Under the old
        # arithmetic periods 47-50 overflowed into the next day and were discarded.
        first = self.convert("2023-10-29", 1)
        last = self.convert("2023-10-29", 50)
        assert first == pd.Timestamp("2023-10-28 23:00")
        assert last == pd.Timestamp("2023-10-29 23:30")
        assert (last - first) == pd.Timedelta(hours=24, minutes=30)

    def test_periods_are_strictly_increasing_across_a_clock_change(self):
        periods = pd.Series(range(1, 51))
        dates = pd.Series(["2023-10-29"] * 50)
        out = transform.settlement_period_to_utc(dates, periods)
        assert out.is_monotonic_increasing
        assert out.is_unique


class TestCollapsePriceProviders:
    def test_weights_by_volume_rather_than_taking_a_simple_mean(self):
        # A thin provider at £100 and a deep one at £50 must not average to £75
        df = pd.DataFrame(
            {
                "startTime": ["2020-01-01T00:00:00Z"] * 2,
                "price": [100.0, 50.0],
                "volume": [1.0, 9.0],
            }
        )

        out = transform.collapse_price_providers(df)

        assert len(out) == 1
        assert out["price"].iloc[0] == pytest.approx(55.0)

    def test_drops_periods_with_no_volume(self):
        # Zero total volume would divide by zero; those periods carry no price
        df = pd.DataFrame(
            {
                "startTime": ["2020-01-01T00:00:00Z", "2020-01-01T00:30:00Z"],
                "price": [50.0, 60.0],
                "volume": [0.0, 10.0],
            }
        )

        out = transform.collapse_price_providers(df)

        assert out["startTime"].tolist() == ["2020-01-01T00:30:00Z"]
