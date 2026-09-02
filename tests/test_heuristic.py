"""Tests for the fixed time-of-day baseline.

The point of this strategy is that it ignores prices, so the tests check it dispatches on
the clock regardless of what prices do, and that it still respects the physical limits.
"""

import numpy as np
import pytest

from gbmo.arbitrage import heuristic
from gbmo.arbitrage.lp import BatterySpec

# 48 half-hours, 50 MW / 100 MWh, matching the 2h_50mw spec
SPEC = BatterySpec("2h_50mw", power_mw=50, capacity_mwh=100, round_trip_efficiency=0.85)
FLAT = np.full(48, 50.0)


class TestClockDispatch:
    def test_charges_only_in_the_charge_window(self):
        d = heuristic.solve_day(FLAT, SPEC)
        outside = np.delete(d.charge_mw, list(heuristic.CHARGE_WINDOW))
        assert outside.max() == pytest.approx(0.0)

    def test_discharges_only_in_the_discharge_window(self):
        d = heuristic.solve_day(FLAT, SPEC)
        outside = np.delete(d.discharge_mw, list(heuristic.DISCHARGE_WINDOW))
        assert outside.max() == pytest.approx(0.0)

    def test_ignores_prices_entirely(self):
        # An inverted price shape, where the rule is exactly wrong, must not change it
        inverted = np.full(48, 10.0)
        inverted[list(heuristic.CHARGE_WINDOW)] = 500.0
        inverted[list(heuristic.DISCHARGE_WINDOW)] = 1.0

        normal = heuristic.solve_day(FLAT, SPEC)
        perverse = heuristic.solve_day(inverted, SPEC)

        assert perverse.charge_mw == pytest.approx(normal.charge_mw)
        assert perverse.discharge_mw == pytest.approx(normal.discharge_mw)
        # And it should lose money doing so
        assert perverse.revenue < 0


class TestPhysicalLimits:
    def test_never_exceeds_capacity(self):
        d = heuristic.solve_day(FLAT, SPEC)
        assert d.soc_mwh.max() <= SPEC.capacity_mwh + 1e-9

    def test_never_exceeds_power_rating(self):
        d = heuristic.solve_day(FLAT, SPEC)
        assert max(d.charge_mw.max(), d.discharge_mw.max()) <= SPEC.power_mw + 1e-9

    def test_never_charges_and_discharges_together(self):
        d = heuristic.solve_day(FLAT, SPEC)
        assert np.minimum(d.charge_mw, d.discharge_mw).max() == pytest.approx(0.0)

    def test_state_of_charge_never_goes_negative(self):
        d = heuristic.solve_day(FLAT, SPEC)
        assert d.soc_mwh.min() >= -1e-9

    def test_a_window_shorter_than_the_duration_leaves_the_store_part_full(self):
        # The 4-hour battery cannot fill from a 4-hour window at 50 MW: 4h * 50 MW is
        # 200 MWh of grid energy, but only 200 * 0.922 = 184 MWh reaches the store.
        four_hour = BatterySpec("4h_50mw", power_mw=50, capacity_mwh=200,
                                round_trip_efficiency=0.85)
        d = heuristic.solve_day(FLAT, four_hour)
        assert d.soc_mwh.max() < four_hour.capacity_mwh
        assert d.soc_mwh.max() == pytest.approx(200 * four_hour.one_way_efficiency, rel=1e-6)


class TestRevenue:
    def test_earns_on_a_favourable_shape(self):
        prices = np.full(48, 50.0)
        prices[list(heuristic.CHARGE_WINDOW)] = 10.0
        prices[list(heuristic.DISCHARGE_WINDOW)] = 200.0

        d = heuristic.solve_day(prices, SPEC)
        assert d.revenue > 0
