"""Perfect-foresight dispatch: the ceiling every other strategy is measured against.

Given prices that are known in advance, the best possible battery schedule is the
solution to a small mixed-integer program. No strategy operating on forecasts can beat
it, which is what makes it the denominator for "percentage of optimum captured".

That also means it is deliberately unrealistic in two ways worth stating. It knows the
future, and with `max_cycles_per_day` unset it will take every profitable spread
including many shallow ones that a real operator would decline because each cycle spends
warranty life. It is an upper bound, not a target.

Formulation, per day, over T settlement periods of h = 0.5 hours:

    variables   c_t  charge power      MW,  0 <= c_t <= P
                d_t  discharge power   MW,  0 <= d_t <= P
                s_t  state of charge   MWh at the end of period t
                z_t  direction flag    binary, 1 when charging

    maximise    sum_t  h * price_t * (d_t - c_t)

    subject to  s_t = s_{t-1} + h*eta*c_t - h*d_t/eta       (energy balance)
                min_soc <= s_t <= capacity
                c_t <= P*z_t,  d_t <= P*(1 - z_t)           (one direction per period)

One-way efficiency `eta` is the square root of the round-trip figure, applied to each
leg, which is the usual convention. Losses are therefore asymmetric in the balance
equation: energy going in is scaled down, energy coming out is scaled up.
"""

from dataclasses import dataclass

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

PERIOD_HOURS = 0.5

# Simultaneous charge and discharge has to be forbidden outright, not merely discouraged.
#
# A first version relied on a small throughput penalty to break what was assumed to be a
# tie. It is not a tie. Through negative prices the behaviour is strictly profitable: at
# -£30/MWh, charging earns £15 a period while discharging costs £12.75, and the round-trip
# loss lets a full battery keep consuming by burning energy it has just stored. The
# optimiser found this immediately and made £2.25 a period from it.
#
# Whether that is physical is genuinely arguable. A single battery cannot charge and
# discharge at the same instant, but it can alternate within a half-hour settlement
# period, which averages to exactly this. The reason to forbid it anyway is that the
# model prices energy and nothing else: cycling to harvest negative prices spends
# warranty life, and a model that ignores degradation would systematically overstate the
# value of doing it. Forbidding it is the conservative choice and matches the CHECK
# constraint on the dispatch table.
#
# The cost is a binary per period, making this a MILP rather than an LP. At 48 binaries
# a day HiGHS solves it in single-digit milliseconds.
THROUGHPUT_TIEBREAK = 1e-6


@dataclass(frozen=True)
class BatterySpec:
    """Mirrors a `battery_spec` row. Duration is capacity / power, never stored."""

    name: str
    power_mw: float
    capacity_mwh: float
    round_trip_efficiency: float
    min_soc_mwh: float = 0.0

    @property
    def one_way_efficiency(self) -> float:
        return float(np.sqrt(self.round_trip_efficiency))

    @property
    def duration_hours(self) -> float:
        return self.capacity_mwh / self.power_mw


@dataclass(frozen=True)
class Dispatch:
    """A solved schedule. Arrays are per settlement period, in order."""

    charge_mw: np.ndarray
    discharge_mw: np.ndarray
    soc_mwh: np.ndarray
    revenue: float
    status: str

    @property
    def ok(self) -> bool:
        return self.status == "optimal"


def _build_energy_balance(n_periods, spec, initial_soc):
    """The equality constraints A_eq @ x = b_eq, one row per period.

    Row t states  s_t - s_{t-1} - h*eta*c_t + (h/eta)*d_t = 0, with s_{-1} taken as the
    opening state of charge, which is why only the first row has a non-zero right side.

    Variables are laid out as [c_0..c_T-1, d_0..d_T-1, s_0..s_T-1, z_0..z_T-1], so the
    column of c_t is t, of d_t is T + t, of s_t is 2T + t and of the direction flag z_t
    is 3T + t.
    """
    h, eta = PERIOD_HOURS, spec.one_way_efficiency
    rows, cols, vals = [], [], []

    for t in range(n_periods):
        rows += [t, t, t]
        cols += [t, n_periods + t, 2 * n_periods + t]
        vals += [-h * eta, h / eta, 1.0]
        if t > 0:
            rows.append(t)
            cols.append(2 * n_periods + t - 1)
            vals.append(-1.0)

    a_eq = coo_matrix((vals, (rows, cols)), shape=(n_periods, 4 * n_periods)).tocsr()
    b_eq = np.zeros(n_periods)
    b_eq[0] = initial_soc
    return a_eq, b_eq


def _build_direction_exclusion(n_periods, power_mw):
    """Constraints tying each period to a single direction via its binary flag.

        c_t <= P * z_t          charging only permitted when z_t = 1
        d_t <= P * (1 - z_t)    discharging only permitted when z_t = 0

    Rearranged for a matrix form with constants on the right:
        c_t - P*z_t <= 0
        d_t + P*z_t <= P
    """
    rows, cols, vals = [], [], []

    for t in range(n_periods):
        rows += [t, t]
        cols += [t, 3 * n_periods + t]
        vals += [1.0, -power_mw]

        rows += [n_periods + t, n_periods + t]
        cols += [n_periods + t, 3 * n_periods + t]
        vals += [1.0, power_mw]

    matrix = coo_matrix(
        (vals, (rows, cols)), shape=(2 * n_periods, 4 * n_periods)
    ).tocsr()
    upper = np.concatenate([np.zeros(n_periods), np.full(n_periods, power_mw)])
    return LinearConstraint(matrix, lb=-np.inf, ub=upper)


def solve_day(prices, spec, initial_soc=0.0, final_soc=0.0):
    """Optimal dispatch for one day of known prices.

    `initial_soc` and `final_soc` both default to empty, which makes days independent and
    directly comparable. It forbids carrying charge overnight, so the result is a slight
    underestimate of the true multi-day optimum; for a battery of four hours or less the
    spreads worth capturing are intraday, so the loss is small and the gain in
    tractability and interpretability is large.
    """
    prices = np.asarray(prices, dtype=float)
    n = len(prices)
    h = PERIOD_HOURS

    # Revenue is earned on discharge and paid on charge. The solver minimises, so the
    # objective is negated. The tiebreak no longer carries the exclusion (the binaries
    # do) but is kept to keep degenerate flat regions deterministic.
    cost = np.concatenate([
        h * prices + THROUGHPUT_TIEBREAK,    # charging costs money
        -h * prices + THROUGHPUT_TIEBREAK,   # discharging earns it
        np.zeros(n),                          # holding charge is free
        np.zeros(n),                          # the direction flag itself is free
    ])

    a_eq, b_eq = _build_energy_balance(n, spec, initial_soc)
    balance = LinearConstraint(a_eq, lb=b_eq, ub=b_eq)
    exclusion = _build_direction_exclusion(n, spec.power_mw)

    lower = np.concatenate([
        np.zeros(n), np.zeros(n), np.full(n, spec.min_soc_mwh), np.zeros(n),
    ])
    upper = np.concatenate([
        np.full(n, spec.power_mw), np.full(n, spec.power_mw),
        np.full(n, spec.capacity_mwh), np.ones(n),
    ])
    # Pinning the closing state as a bound rather than another equality keeps the
    # constraint matrix square and the model easier to read.
    lower[3 * n - 1] = upper[3 * n - 1] = final_soc

    integrality = np.concatenate([np.zeros(3 * n), np.ones(n)])

    result = milp(
        c=cost,
        integrality=integrality,
        bounds=Bounds(lower, upper),
        constraints=[balance, exclusion],
    )

    if result.x is None:
        return Dispatch(
            charge_mw=np.zeros(n), discharge_mw=np.zeros(n), soc_mwh=np.zeros(n),
            revenue=0.0, status=str(result.message).split(".")[0].strip().lower(),
        )

    charge, discharge, soc = result.x[:n], result.x[n:2 * n], result.x[2 * n:3 * n]

    # A solver returns values good to its own tolerance, so a flow that should be zero
    # can come back as -0.0 or -1e-15. The dispatch table requires non-negative flows,
    # and rounding here is honest: anything this small is solver noise, not dispatch.
    charge = np.clip(charge, 0.0, spec.power_mw)
    discharge = np.clip(discharge, 0.0, spec.power_mw)
    soc = np.clip(soc, spec.min_soc_mwh, spec.capacity_mwh)

    # Report the true revenue, not the objective: the objective carries the tiebreak.
    revenue = float(h * np.dot(prices, discharge - charge))

    return Dispatch(
        charge_mw=charge, discharge_mw=discharge, soc_mwh=soc,
        revenue=revenue, status="optimal",
    )
