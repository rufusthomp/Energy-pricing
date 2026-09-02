# GB battery arbitrage — design and findings

Working notes, not a write-up. Everything here is reproducible from the repository at
commit `32fa49f`.

---

## 1. The question

How much of the theoretical wholesale arbitrage value can a GB battery capture, how does
that depend on duration, and how has it changed as the price shape changed?

Framed as a counterfactual rather than a reconstruction: *given how GB prices actually
evolved, what would each duration have earned?* The 4-hour asset did not exist in GB in
2018, so its early years are hypothetical by construction.

## 2. Data

| | |
| --- | --- |
| Source | NESO generation mix and demand; Elexon Market Index Price (MID) |
| Backtest window | 2018-01-01 to 2026-06-20 |
| Complete days | 2,922 (all 48 periods priced) |
| Excluded | 132 partial days, 38 with no price |
| Priced periods used | 140,256 |

Bounded by price coverage, not generation: MID begins in 2018 while generation and demand
run from 2009. The battery study spans eight and a half years, not seventeen.

Price shape over the window, per year:

| Year | Mean | Max | Negative periods |
| --- | --- | --- | --- |
| 2018 | 56.8 | 321 | 18 |
| 2019 | 41.9 | 152 | 60 |
| 2020 | 33.4 | 511 | 329 |
| 2021 | 115.4 | 1,984 | 65 |
| 2022 | 197.0 | 1,562 | 133 |
| 2023 | 93.4 | 580 | 428 |
| 2024 | 70.8 | 605 | 495 |
| 2025 | 79.5 | 1,353 | 489 |
| 2026* | 91.6 | 291 | 175 |

\* to 20 June. Negative pricing rose roughly 27-fold from 2018 to 2024.

## 3. Method

A ladder of strategies, each measured against the same ceiling.

| Rung | Strategy | Status |
| --- | --- | --- |
| 1 | Perfect-foresight MILP | done — the ceiling |
| 2 | Fixed time-of-day rule | done — the floor |
| 3 | LSTM forecast into a receding-horizon optimiser | not started |
| 4 | RL agent | not started |

**Metric: percentage of the perfect-foresight optimum captured.** The ceiling is exactly
solvable, so every strategy has an interpretable denominator. A rung that loses to the
floor is a reportable result.

Batteries: 50 MW throughout, 0.85 round-trip, differing only in duration (1h / 2h / 4h).
Power is held constant deliberately — for a price-taker, value scales roughly linearly
with power, so varying it isolates nothing.

## 4. Design decisions

**Days are solved independently**, opening and closing empty. Forbids overnight carry, so
slightly understates the true optimum; for a battery of four hours or less the spreads
worth capturing are intraday.

**Simultaneous charge and discharge is forbidden**, which required a MILP rather than an
LP. It is not a degenerate tie: at negative prices it is strictly profitable, because
charging is paid while the round-trip loss lets a full battery keep consuming. Worth
£2.25 a period on the test case. Forbidden because the model prices energy and nothing
else, so permitting it would overstate the value of behaviour that in reality spends
warranty life.

**Model outputs are stored, profit is not.** Dispatch and forecasts are observations of a
run, keyed to a `model_run` row recording commit, config and seed. Profit is a join of
dispatch against price, so it is computed.

**Physical limits are enforced after the write, not by constraints.** A Postgres CHECK
sees only its own row, and capacity and power rating live in `battery_spec`. The
same-row conditions are constraints; the cross-table ones are queries the harness runs
before a run counts.

## 5. Findings

### 5.1 Ceiling and floor

50 MW battery, whole window:

| Duration | Ceiling £/MW/yr | Naive captures |
| --- | --- | --- |
| 1h | 24,899 | 24.1% |
| 2h | 42,374 | 37.8% |
| 4h | 64,775 | 52.0% |

Ceiling by year, £ thousand:

| Year | 1h | 2h | 4h |
| --- | --- | --- | --- |
| 2018 | 437 | 768 | 1,154 |
| 2019 | 465 | 798 | 1,204 |
| 2020 | 661 | 1,090 | 1,645 |
| 2021 | 1,955 | 3,260 | 4,841 |
| 2022 | 2,682 | 4,531 | 6,912 |
| 2023 | 1,535 | 2,534 | 3,803 |
| 2024 | 1,106 | 1,919 | 3,006 |
| 2025 | 1,196 | 2,132 | 3,381 |
| 2026* | 506 | 913 | 1,485 |

### 5.2 The duration advantage is U-shaped, not rising

4-hour ceiling as a multiple of the 1-hour ceiling:

| 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026* |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.64 | 2.59 | 2.49 | 2.48 | 2.58 | 2.48 | 2.72 | 2.83 | 2.93 |

The prior hypothesis was that longer duration would gain steadily as renewables grew. It
did not. The ratio falls to 2.48 through 2020-23 and then climbs to 2.93.

Reading: when spreads concentrate into a few extreme periods, as in the gas crisis, a
short battery captures most of the available value because an hour is enough to exploit a
£1,984 spike. The climb since 2023 is a wider, flatter, solar-shaped curve that pays for
spanning more of the day. Longer duration wins by more now than at any point in the
window, but it was not a steady trend.

### 5.3 Capture rate: no trend established

Naive rule as a percentage of the ceiling at the same duration:

| Year | 1h | 2h | 4h |
| --- | --- | --- | --- |
| 2018 | 25.5 | 38.9 | 56.1 |
| 2019 | 25.8 | 39.2 | 55.2 |
| 2020 | 29.2 | 43.8 | 57.7 |
| 2021 | 31.6 | 50.1 | 63.9 |
| 2022 | 25.5 | 38.3 | 52.4 |
| 2023 | 18.2 | 30.9 | 46.8 |
| 2024 | 26.4 | 39.4 | 52.8 |
| 2025 | 18.7 | 30.9 | 44.2 |

An earlier draft claimed this was decaying, on the grounds that 2018 is higher than 2025.
That claim does not survive a line fit. Slopes are -0.99, -1.26 and -1.66 percentage
points per year for the 1h, 2h and 4h batteries, with t statistics of -1.51, -1.37 and
-2.13 on six degrees of freedom. The strongest reaches p of roughly 0.08. Eight annual
observations dominated by one unusual year (2021) cannot carry a trend.

The hypothesis remains reasonable: as the mix decarbonises, prices become weather-driven
rather than demand-driven, so a fixed-clock rule should lose ground. Testing it properly
needs three changes:

1. **Finer granularity.** Monthly capture rates give around 100 observations rather than 8.
2. **The right regressor.** Decarbonisation is the mechanism, so regress on renewable
   share of generation, which is measurable from the generation table, rather than on
   time, which is only a proxy and is confounded by the gas crisis.
3. **A competent strategy.** The naive rule is a floor, not an operator. Whether a
   forecaster's capture rate moves with renewable share is the question that matters.

2026 is excluded throughout: it is a half year to 20 June.

### 5.4 Incidental: a demand timezone defect

GB settlement periods are defined on the local clock (46 periods on the spring change, 50
on the autumn one); the generation and price feeds are true UTC. The loader had been
adding the period offset to a naive date and joining against the UTC dimension, attaching
demand an hour late throughout BST and pushing the long October day's last periods into
the next day where they were discarded.

Fixing it recovered 34 rows and moved marginal-fuel attribution by up to 5 percentage
points, while annual price errors barely shifted (mean absolute v2 error 7.83 to 8.01
per MWh). The merit-order headline survived: gas sets the price 64.7% of priced periods
under v2, against the ~65% previously documented.

## 6. Definitions

Terms used above, stated precisely because several were used loosely first.

**Ceiling** (perfect-foresight optimum). The maximum revenue obtainable by any dispatch
schedule that respects the battery's constraints, given the prices that actually
occurred. Not an abstract maximum: it is relative to the constraint set imposed here,
namely days solved independently, store empty at both ends, one direction per settlement
period, no cycle limit. Loosening any of those raises it.

**Floor.** Revenue from the fixed time-of-day rule, which dispatches on the clock and
never looks at a price.

**Capture rate.** For a strategy S, battery B and window W:

    capture(S, B, W) = revenue(S, B, W) / revenue(ceiling, B, W)

The fraction of theoretically available money the strategy actually got. Bounded above by
1 by construction, unbounded below: a strategy can lose money and score negative. Always
quoted against the same battery and the same window, since a 4h ceiling is not comparable
to a 1h one.

**Spread.** The difference between two prices. Ambiguous unless qualified: "daily spread"
means the maximum minus the minimum price within a day, which is not the same as the
spread a battery actually trades across.

**Duration.** capacity_mwh / power_mw. Hours to discharge fully at rated power. Never
stored, always derived.

**Round-trip efficiency.** Energy returned to the grid divided by energy drawn from it,
over a full cycle. 0.85 here. **One-way efficiency** is its square root, 0.922, applied
to each leg by convention. **Break-even premium** is 1/round-trip minus 1, so 17.6%: the
margin by which the sell price must beat the buy price before a cycle earns anything.

**Price-taker.** The assumption that the asset's own dispatch does not move the price.
Defensible for 50 MW against 20-45 GW of demand; invalid for a fleet, which is why this
model cannot answer questions about deployment.

**Level and shape.** Level is a day's mean price; shape is the deviation of each period
from it. Dispatch depends only on shape, because adding a constant to every price in a
day leaves the optimal schedule unchanged.

**Receding horizon** (model predictive control). Re-optimise at every step using a
forecast, execute only the first action, then re-forecast and re-optimise. Distinct from
committing to a whole day's schedule in advance.

**Regime.** A stretch over which the price-generating process is stable. 2021-22 is a
different regime from 2019, which is why fitting one trend across the whole window is
fragile.

## 7. Limitations

- **Perfect foresight with no cycle limit.** The ceiling takes every profitable spread
  including shallow ones a real operator would decline. It is an upper bound, not a target.
- **Wholesale only.** No Balancing Mechanism, no ancillary services. GB batteries earn
  most of their revenue there, so these figures are not fleet revenue.
- **No degradation.** A cycling cost in £/MWh of throughput is the obvious next model.
- **Price-taker.** Fine at 50 MW against 20-45 GW of demand; breaks at scale.
- **Constant efficiency across the window**, which conflates technology improvement with
  price-shape change. Held fixed deliberately to isolate the latter.
- **2026 is a half year** to 20 June. Read that row as seasonal, not as collapse.
- **4h before ~2024 is hypothetical.** No such asset existed in GB.

## 8. Open

- Rung 3: LSTM forecast into the same optimiser over a receding horizon.
- Rung 4: RL agent on the same metric.
- Sensitivity: round-trip efficiency, given the break-even premium is 17.6% at 0.85.
- Derive the vintage path (what the market actually built each year) from the factorial.
