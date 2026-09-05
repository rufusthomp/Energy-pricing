"""Tests for the ENTSO-E ingest transforms.

Everything here is pure and runs without a security token. The parts that need the
network (`fetch`, `populate_cache`, `verify_currencies`) are deliberately not mocked:
mocking an HTTP client tests the mock, and the real failure modes on this source are the
platform returning something unexpected, which no fixture would predict.

What is covered is the logic that fails silently and directionally: timezone handling,
resolution inference, and the production-type aggregation that feeds the panel's
treatment variable.
"""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from gbmo.ingest import entsoe, load_zones
from gbmo.ingest.zones import CATEGORIES, CATEGORY_BY_PRODUCTION_TYPE, ZONES


def local_index(start, periods, freq, tz):
    return pd.date_range(start, periods=periods, freq=freq, tz=tz)


class TestFetchEndDate:
    """The current year is clamped to the publication lag; past years are not."""

    def test_past_year_is_unclamped(self):
        assert entsoe.fetch_end_date(2020, today=date(2026, 9, 5)) == date(2020, 12, 31)

    def test_current_year_stops_at_the_lag_boundary(self):
        assert entsoe.fetch_end_date(2026, today=date(2026, 9, 5)) == date(2026, 9, 3)

    def test_a_year_entirely_beyond_the_boundary_yields_no_window(self, monkeypatch):
        monkeypatch.setattr(entsoe, "fetch_end_date", lambda year, today=None: date(2026, 9, 3))
        assert entsoe.request_window("GB", 2030) is None


class TestRequestWindow:
    """The window is the zone's own calendar year, not a UTC one shifted by its offset."""

    def test_window_is_localised_to_the_zone(self):
        start, _ = entsoe.request_window("DK_1", 2020)
        assert str(start.tz) == "Europe/Copenhagen"
        assert start.year == 2020 and start.month == 1 and start.day == 1

    def test_zones_in_different_offsets_start_at_different_instants(self):
        gb_start, _ = entsoe.request_window("GB", 2020)
        dk_start, _ = entsoe.request_window("DK_1", 2020)
        # Both are local midnight on 1 January, an hour apart in absolute time
        assert gb_start.tz_convert("UTC") - dk_start.tz_convert("UTC") == pd.Timedelta(hours=1)

    def test_end_is_exclusive_and_one_day_past_the_last_date(self):
        _, end = entsoe.request_window("FR", 2020)
        assert end.date() == date(2021, 1, 1)


class TestToUtcNaive:
    """Naive UTC, matching every other table in the schema."""

    def test_index_becomes_naive(self):
        frame = pd.DataFrame({"price": [1.0, 2.0]},
                             index=local_index("2020-06-01", 2, "h", "Europe/Berlin"))
        out = entsoe.to_utc_naive(frame)
        assert out.index.tz is None
        assert out.index.name == "datetime"

    def test_summer_offset_is_applied(self):
        # Berlin is UTC+2 in June, so local 12:00 is 10:00Z
        frame = pd.DataFrame({"price": [1.0]},
                             index=local_index("2020-06-01 12:00", 1, "h", "Europe/Berlin"))
        assert entsoe.to_utc_naive(frame).index[0] == pd.Timestamp("2020-06-01 10:00")

    def test_the_repeated_local_hour_becomes_two_distinct_utc_hours(self):
        """The clock change that bit the GB pipeline, in its European form.

        On 25 October 2020 Berlin ran 02:00-03:00 twice. In local time those are the same
        wall clock; in UTC they are 00:00Z and 01:00Z, and must stay distinct or the load
        silently drops one of them on the primary key.
        """
        index = local_index("2020-10-25 00:00", 5, "h", "Europe/Berlin")
        frame = pd.DataFrame({"price": range(5)}, index=index)
        out = entsoe.to_utc_naive(frame)
        assert out.index.is_unique
        assert len(out) == 5


class TestResolutionMinutes:
    def test_hourly(self):
        assert entsoe.resolution_minutes(local_index("2020-01-01", 48, "h", "UTC")) == 60

    def test_quarter_hourly(self):
        assert entsoe.resolution_minutes(local_index("2025-11-01", 96, "15min", "UTC")) == 15

    def test_a_single_missing_hour_does_not_change_the_answer(self):
        index = local_index("2020-01-01", 48, "h", "UTC").delete(10)
        assert entsoe.resolution_minutes(index) == 60

    def test_degenerate_index_defaults_to_hourly(self):
        assert entsoe.resolution_minutes(pd.DatetimeIndex([])) == 60
        assert entsoe.resolution_minutes(local_index("2020-01-01", 1, "h", "UTC")) == 60


class TestFlattenGenerationColumns:
    def test_flat_columns_pass_through(self):
        frame = pd.DataFrame({"Solar": [1.0]}, index=local_index("2020-06-01", 1, "h", "UTC"))
        assert list(entsoe.flatten_generation_columns(frame).columns) == ["Solar"]

    def test_consumption_leg_is_labelled_and_kept(self):
        columns = pd.MultiIndex.from_tuples([
            ("Hydro Pumped Storage", "Actual Aggregated"),
            ("Hydro Pumped Storage", "Actual Consumption"),
            ("Solar", "Actual Aggregated"),
        ])
        frame = pd.DataFrame([[10.0, 4.0, 2.0]],
                             index=local_index("2020-06-01", 1, "h", "UTC"), columns=columns)
        out = entsoe.flatten_generation_columns(frame)
        assert list(out.columns) == [
            "Hydro Pumped Storage", "Hydro Pumped Storage [consumption]", "Solar"]


class TestToHourly:
    def test_quarter_hours_average_into_the_hour(self):
        index = local_index("2025-11-01", 4, "15min", "UTC").tz_localize(None)
        frame = pd.DataFrame({"price": [10.0, 20.0, 30.0, 40.0]}, index=index)
        out = load_zones.to_hourly(frame)
        assert len(out) == 1
        assert out["price"].iloc[0] == pytest.approx(25.0)

    def test_hourly_input_is_unchanged(self):
        index = local_index("2020-01-01", 3, "h", "UTC").tz_localize(None)
        frame = pd.DataFrame({"price": [1.0, 2.0, 3.0]}, index=index)
        # check_freq=False: resampling stamps a freq on the index that the input lacks.
        # The claim under test is that no value moves, not that metadata matches.
        pd.testing.assert_frame_equal(load_zones.to_hourly(frame), frame, check_freq=False)

    def test_a_gap_does_not_become_a_row_of_nulls(self):
        """Resampling spans gaps by construction; the empty hours must not be written."""
        index = pd.DatetimeIndex(["2020-01-01 00:00", "2020-01-01 05:00"])
        frame = pd.DataFrame({"price": [1.0, 2.0]}, index=index)
        assert len(load_zones.to_hourly(frame)) == 2


class TestAggregateGeneration:
    def frame(self, columns):
        """One hour of generation. Takes a mapping, not keywords: most ENTSO-E
        production types contain spaces and are not valid Python identifiers."""
        index = pd.DatetimeIndex(["2020-06-01 00:00"])
        return pd.DataFrame({k: [v] for k, v in columns.items()}, index=index)

    def test_wind_sums_onshore_and_offshore(self):
        out = load_zones.aggregate_generation(
            self.frame({"Wind Onshore": 100.0, "Wind Offshore": 50.0}))
        assert out["wind_mw"].iloc[0] == pytest.approx(150.0)

    def test_every_fossil_type_lands_in_one_category(self):
        out = load_zones.aggregate_generation(
            self.frame({"Fossil Gas": 10.0, "Fossil Hard coal": 5.0,
                          "Fossil Brown coal/Lignite": 2.0, "Fossil Oil": 1.0}))
        assert out["fossil_mw"].iloc[0] == pytest.approx(18.0)

    def test_pumped_storage_is_storage_not_hydro(self):
        """The incumbent arbitrageur is a variable of interest, not background hydro."""
        out = load_zones.aggregate_generation(
            self.frame({"Hydro Pumped Storage": 40.0,
                          "Hydro Water Reservoir": 60.0}))
        assert out["storage_mw"].iloc[0] == pytest.approx(40.0)
        assert out["hydro_mw"].iloc[0] == pytest.approx(60.0)

    def test_consumption_leg_is_excluded(self):
        """Netting a zone's pumping against its own generation would understate both."""
        out = load_zones.aggregate_generation(
            self.frame({"Hydro Pumped Storage": 40.0,
                          "Hydro Pumped Storage [consumption]": 25.0}))
        assert out["storage_mw"].iloc[0] == pytest.approx(40.0)

    def test_unreported_category_is_null_not_zero(self):
        """A zone that reports no solar line has not reported zero solar."""
        out = load_zones.aggregate_generation(self.frame({"Wind Onshore": 100.0}))
        assert np.isnan(out["solar_mw"].iloc[0])

    def test_a_reported_zero_stays_zero(self):
        out = load_zones.aggregate_generation(self.frame({"Solar": 0.0}))
        assert out["solar_mw"].iloc[0] == 0.0

    def test_unknown_production_type_raises(self):
        """Silently excluding a new fuel would inflate renewable share: the treatment."""
        with pytest.raises(load_zones.UnknownProductionType, match="Fusion"):
            load_zones.aggregate_generation(self.frame({"Fusion": 1.0}))

    def test_unknown_production_type_can_be_excluded_knowingly(self):
        out = load_zones.aggregate_generation(
            self.frame({"Fusion": 1.0, "Solar": 2.0}), allow_unknown=True)
        assert out["solar_mw"].iloc[0] == pytest.approx(2.0)

    def test_every_category_gets_a_column(self):
        out = load_zones.aggregate_generation(self.frame({"Solar": 1.0}))
        assert list(out.columns) == [f"{c}_mw" for c in CATEGORIES]


class TestZoneReference:
    def test_zone_codes_are_unique(self):
        codes = [z[0] for z in ZONES]
        assert len(codes) == len(set(codes))

    def test_every_zone_code_is_a_real_entsoe_area(self):
        from entsoe.mappings import Area
        areas = {a.name for a in Area}
        assert not [z[0] for z in ZONES if z[0] not in areas]

    def test_zone_timezone_matches_the_platform(self):
        """A wrong timezone shifts a zone's whole series and looks like a lead or lag."""
        from entsoe.mappings import Area
        mismatched = [(z[0], z[3], Area[z[0]].tz) for z in ZONES if z[3] != Area[z[0]].tz]
        assert not mismatched

    def test_every_mapped_production_type_is_one_entsoe_publishes(self):
        from entsoe.mappings import PSRTYPE_MAPPINGS
        published = set(PSRTYPE_MAPPINGS.values())
        assert not [t for t in CATEGORY_BY_PRODUCTION_TYPE if t not in published]

    def test_every_category_is_reachable(self):
        assert set(CATEGORY_BY_PRODUCTION_TYPE.values()) == set(CATEGORIES)

    def test_currencies_are_three_letter_codes(self):
        assert all(len(z[4]) == 3 and z[4].isupper() for z in ZONES)
