"""Tests for the perfect-foresight LP.

The cases here are hand-computable on purpose. An optimiser that returns a plausible
number is not evidence of anything; these check it returns the number the arithmetic
demands, and that it declines trades it should decline.
"""

import numpy as np
import pytest

from gbmo.arbitrage.lp import BatterySpec, solve_day

LOSSLESS = BatterySpec("lossless", power_mw=1, capacity_mwh=1, round_trip_efficiency=1.0)
REALISTIC = BatterySpec("realistic", power_mw=1, capacity_mwh=1, round_trip_efficiency=0.85)


class TestSpec:
    def test_one_way_efficiency_is_the_square_root(self):
        assert REALISTIC.one_way_efficiency == pytest.approx(0.92195, abs=1e-5)

    def test_duration_is_capacity_over_power(self):
        assert BatterySpec("4h", power_mw=50, capacity_mwh=200,
                           round_trip_efficiency=0.85).duration_hours == 4.0


class TestLosslessArithmetic:
    def test_buys_cheap_and_sells_dear_for_the_exact_expected_revenue(self):
        # Two periods at £10 fill the 1 MWh store (0.5 MWh each), two at £100 empty it.
        # Revenue = 0.5*1*(100+100) - 0.5*1*(10+10) = 90
        d = solve_day([10, 10, 100, 100], LOSSLESS)

        assert d.ok
        assert d.revenue == pytest.approx(90.0)
        assert d.charge_mw == pytest.approx([1, 1, 0, 0])
        assert d.discharge_mw == pytest.approx([0, 0, 1, 1])
        assert d.soc_mwh == pytest.approx([0.5, 1.0, 0.5, 0.0])

    def test_flat_prices_produce_no_trading(self):
        d = solve_day([50] * 8, LOSSLESS)
        assert d.revenue == pytest.approx(0.0)
        assert d.charge_mw == pytest.approx(np.zeros(8))


class TestEfficiencyLosses:
    def test_round_trip_loss_is_exactly_the_stated_figure(self):
        # 1 MWh drawn from the grid returns 0.85 MWh to it, so buying at 10 and
        # selling at 100 earns 0.85*100 - 1*10 = 75
        d = solve_day([10, 10, 100, 100], REALISTIC)
        assert d.revenue == pytest.approx(75.0, abs=1e-6)

    @pytest.mark.parametrize(
        "premium, trades",
        [(1.10, False), (1.15, False), (1.20, True), (1.50, True)],
    )
    def test_declines_spreads_below_the_break_even_premium(self, premium, trades):
        # At 0.85 round-trip a cycle needs the sell price to beat the buy price by
        # 1/0.85, about 17.6%, before it is worth doing at all.
        d = solve_day([100, 100, 100 * premium, 100 * premium], REALISTIC)
        assert (d.revenue > 1e-6) is trades


class TestConstraints:
    def test_never_exceeds_capacity_or_power(self):
        prices = [10, 10, 10, 10, 200, 200, 200, 200]
        spec = BatterySpec("2h", power_mw=1, capacity_mwh=2, round_trip_efficiency=0.9)
        d = solve_day(prices, spec)

        assert d.soc_mwh.max() <= spec.capacity_mwh + 1e-6
        assert d.soc_mwh.min() >= -1e-6
        assert d.charge_mw.max() <= spec.power_mw + 1e-6
        assert d.discharge_mw.max() <= spec.power_mw + 1e-6

    def test_never_charges_and_discharges_in_the_same_period(self):
        # Negative prices flatten the objective with respect to simultaneous flow, which
        # is where a solver is free to return a physically meaningless vertex. The
        # throughput tiebreak exists to stop that, and the dispatch table rejects it.
        d = solve_day([-50, -50, 10, 10, 80, 80, -30, -30], REALISTIC)
        assert np.all(np.minimum(d.charge_mw, d.discharge_mw) < 1e-6)

    def test_closes_the_day_empty(self):
        d = solve_day([10, 10, 100, 100], LOSSLESS)
        assert d.soc_mwh[-1] == pytest.approx(0.0, abs=1e-6)

    def test_opening_charge_can_be_sold(self):
        # Starting full and facing only high prices, the optimiser should empty the store
        d = solve_day([100, 100], LOSSLESS, initial_soc=1.0, final_soc=0.0)
        assert d.revenue == pytest.approx(100.0)
        assert d.charge_mw == pytest.approx([0, 0])


class TestNegativePrices:
    def test_is_paid_to_charge_when_prices_are_negative(self):
        # GB negative pricing went from 18 periods in 2018 to ~490 by 2024, so this is
        # a live case rather than a curiosity: charging is revenue, not cost.
        d = solve_day([-40, -40, 60, 60], LOSSLESS)

        assert d.revenue > 0
        # Paid 0.5*40*2 = 40 to absorb, then sold 1 MWh at 60
        assert d.revenue == pytest.approx(40.0 + 60.0)
