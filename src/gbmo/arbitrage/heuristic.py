"""Fixed time-of-day dispatch: the floor.

Charge overnight, discharge into the evening peak, on a fixed clock and with no
knowledge of prices at all. This is roughly what a battery does if nobody is trading it,
and it is the honest baseline: a strategy that cannot beat this is not earning its
complexity.

The windows are fixed in UTC while the GB evening peak moves with the clock, sitting
around 17:00-19:00 local and therefore an hour earlier in UTC through summer. That
mismatch is not an oversight. A rule that tracked the peak properly would already be
using information, and the point of this baseline is to use none.
"""

import numpy as np

from gbmo.arbitrage.lp import PERIOD_HOURS, Dispatch, clean

# Half-hourly periods, indexed from midnight UTC.
CHARGE_WINDOW = range(8)          # 00:00 - 04:00, the overnight trough
DISCHARGE_WINDOW = range(32, 40)  # 16:00 - 20:00, spanning the evening peak


def solve_day(prices, spec, initial_soc=0.0, charge_window=CHARGE_WINDOW,
              discharge_window=DISCHARGE_WINDOW):
    """Dispatch one day on the clock alone.

    Prices are taken only to value the result, never to decide it. Charging fills at full
    power until the store is full; discharging empties it at full power. Both stop at the
    physical limits, so a battery whose window is shorter than its duration simply does
    not fill.
    """
    prices = np.asarray(prices, dtype=float)
    n = len(prices)
    eta = spec.one_way_efficiency
    h = PERIOD_HOURS

    charge = np.zeros(n)
    discharge = np.zeros(n)
    soc = np.zeros(n)
    level = float(initial_soc)

    for t in range(n):
        if t in charge_window:
            headroom = spec.capacity_mwh - level
            # Grid power that would exactly fill the remaining headroom this period
            power = min(spec.power_mw, headroom / (h * eta)) if headroom > 0 else 0.0
            charge[t] = max(power, 0.0)
            level += h * eta * charge[t]
        elif t in discharge_window:
            available = level - spec.min_soc_mwh
            # Grid power the remaining charge can sustain, after the discharge loss
            power = min(spec.power_mw, available * eta / h) if available > 0 else 0.0
            discharge[t] = max(power, 0.0)
            level -= h * discharge[t] / eta

        soc[t] = level

    charge, discharge, soc = clean(charge, discharge, soc, spec)
    revenue = float(h * np.dot(prices, discharge - charge))
    return Dispatch(charge_mw=charge, discharge_mw=discharge, soc_mwh=soc,
                    revenue=revenue, status="optimal")
