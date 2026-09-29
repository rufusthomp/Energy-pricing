# Pre-registration: Sun is a clock, wind is a lottery

Fixed 2026-09-27, before any panel backtest has been run or any panel outcome computed.
Nothing below may be changed silently. Deviations go in the log at the foot, with the date
and the reason, and the paper reports them.

This refines the question in `research-design.md`. It keeps that document's distinction
between a scale effect and an information effect and its timing rules. It narrows the
treatment from "renewables" to the wind/solar composition, and it changes the
identification for the reason given under "Why not the capacity interaction".

## Question

> Does the composition of renewable output change how much of storage's arbitrage value
> can be captured without a price forecast?

**Hypothesis.** Solar output is diurnal: on a sunny day it deepens a midday trough that
sits at the same clock hours as on every other sunny day. Wind output arrives with weather
systems and has no clock regularity. So solar should raise arbitrage value in a way that
a schedule learned from recent typical days can capture. Wind should raise it, or reshape
it, in ways that need information about the specific day.

**Why it matters.** Whether decarbonisation shifts storage value towards operators with
forecasting capability, which is a market-structure question, would then depend on whether
a system decarbonises through wind or through solar.

## Operators

All operators hold a 1 MW battery with 2 hours of storage and 85% round-trip efficiency,
start and end each delivery day empty, and are price-takers in the day-ahead auction.

| Operator | Information set | Schedule for day d |
| --- | --- | --- |
| **PF**, perfect foresight | actual prices of day d | MILP on day d's prices: the ceiling `V*` |
| **TD**, typical day | prices of days d−28 to d−1 | MILP on the mean price by market hour over those 28 days |
| **PS**, persistence | prices of day d−1 | MILP on day d−1's prices, mapped by market hour |
| **FC**, forecaster (extension) | TD's set plus TSO day-ahead forecasts | MILP on a gradient-boosted price forecast |

Schedules are fixed before day d and settled at day d's actual prices. Every input is
available by 12:00 CET on D−1: day d−1's prices cleared at D−2. FC's wind and solar
forecast timing caveat is as stated in `research-design.md`.

Days are CET delivery days (`entsoe.calendar.delivery_date`), with 23 or 25 hours on
clock-change days. A missing market hour in a profile is dropped, and a repeated one is
reused.

## Sample

**19 zones**: the 21 panel zones minus GB (no ENTSO-E coverage after 2020) and IE_SEM
(almost no load forecast after mid-2021, so its penetration regressors are undefined). The
same 19 are used for the operators and the regressions, so every descriptive statistic
describes the estimation sample.

The window runs from 2019-01-01 to 2026-09-20. It starts later where a zone's first 28
days of history are needed for TD. Zone-days with any missing hour are dropped, and
zone-days where `V*` is below the zone's own 5th percentile are dropped from ratio
outcomes only.

## Variables

For zone z on delivery day d:

- **Treatments.** `wind_pen = Σ forecast wind MWh / Σ forecast load MWh`, and `solar_pen`
  likewise, both from the TSO day-ahead forecasts in percentage points. They are forecasts,
  so they are the right regressors for a day-ahead price.
- **Scale outcome.** `log V*`.
- **Information outcomes.** The capture shares `TD/V*` and `PS/V*`, the key outcome being
  `TD/V*`.
- **Mechanism outcomes.**
  - `novelty = 1 − corr(p_d, TD profile)`: how far day d's shape departs from the
    typical day.
  - The daily spread `max − min`.
- **Placebo regressor.** The forecast error, realised minus forecast wind MWh over forecast
  load. The day-ahead price clears before the error is known, so it should have no effect
  on any day-ahead outcome.

## Specification

    Y_zd = β_w · wind_pen_zd + β_s · solar_pen_zd + α_{z,year} + α_{z,month} + λ_d + ε_zd

- **`α_{z,year}`** absorbs capacity build-out, market reforms and any zone-specific slow
  trend. That is why capacity is not needed.
- **`α_{z,month}`** absorbs each zone's seasonal cycle, including the solar season.
- **`λ_d`** absorbs everything common to Europe on the day: gas, carbon, continental
  weather in part.
- **The residual variation** in `wind_pen` and `solar_pen` is then day-to-day weather
  within a zone-year-month, relative to other zones on the same day.

**Inference.** Standard errors are clustered by zone. With 19 clusters, the reported
p-values for the key coefficients come from a wild cluster bootstrap with Webb weights
and 9,999 draws. Two-way zone and date clustering is a robustness check.

## Hypotheses and predictions

| | Outcome | Prediction |
| --- | --- | --- |
| **H1**, key | `TD/V*` | `β_w < β_s`, the wind coefficient below the solar one. Wind lowers typical-day capture more than solar does. Tested directly as the difference. |
| **H2**, mechanism | novelty | `β_w > 0` and `β_w > β_s`. Wind makes the day's shape less typical. |
| **H3**, scale | `log V*` | Reported without a directional prediction. |
| **H4**, heterogeneity | `TD/V*` | Adding `wind_pen × K_wind`, where `K_wind` is the zone-year mean of `wind_pen`: the wind effect is more negative where wind is already a larger share. |
| **Placebo** | every outcome above | The forecast-error coefficient is not significantly different from zero. |

**Falsification.** If `β_w ≥ β_s` for `TD/V*`, the hypothesis fails. The paper then
reports that renewable composition does not change the information content of storage
value, which is still a result.

## Why not the capacity interaction

`research-design.md` identified the structural effect through a weather anomaly
interacted with installed capacity. Reported capacity turned out to be clean for only 16
zones. Zone×year effects absorb capacity growth entirely, which keeps identification in
weather without needing capacity at all. H4 keeps a version of the interaction, built from
the forecasts themselves.

## Robustness, fixed in advance

- 1h and 4h batteries.
- The ratio floor at the 1st and 10th percentiles.
- Leaving out one zone at a time.
- Two-way clustering.
- A 14-day TD window.
- Dropping the 2021–23 gas crisis.

## Deviation log

**2026-09-27, before any regression was run.** Both were decided with only the operator
backtests in progress and no outcome inspected.

1. **CZ leaves the regression sample.** Czechia publishes no day-ahead wind forecast at
   all (0% of hours), so `wind_pen` is undefined there. Filling it with zero would invent
   data. The regression sample is **18 zones**, with zone-days kept only where both wind
   and solar forecasts cover every hour. CZ stays in the descriptive statistics. Solar
   forecasts are also missing for some years in EE, FI, PL, SE_3 and SE_4; those
   zone-days drop by the same rule.
2. **The gas-crisis window, left unspecified above, is fixed as 2021-07-01 to 2023-06-30**
   for the "dropping the 2021–23 gas crisis" robustness check.
3. **FC's forecast target.** The forecaster predicts the day's deviation from the
   typical-day profile rather than the price level, so it nests TD. FC − TD is then the
   value of day-specific information exactly. It is refitted monthly on an expanding
   window.
4. **Zero-value days.** NO_2 has 609 days (22%) with perfectly flat prices, where V* = 0
   and a capture share is undefined rather than zero. Capture shares now require V* > 0,
   and the 5th-percentile floor is computed among days with V* > 0. No other zone has a
   zero-value day, so only NO_2's floor changes. Found in the frame's summary statistics
   before any regression.
5. **Implausible load forecasts.** Penetrations and the placebo regressor are set to
   missing where the day's load forecast is outside 50–200% of the zone's median for
   that month. This flags 11 days, all reporting errors: EE forecasts at 0–49% of normal,
   one GR day at 3%. The rule was chosen relative to the same month because a flat band
   around the annual median would flag legitimate French winter peaks.

## Exploratory analyses, added after results were seen

**Not pre-registered.** Added 2026-09-27 after the first results, and reported in the
paper under a separate, labelled heading. They cannot be used to change the verdict on
H1.

- **E1, value of information in euros.** Outcomes: `V* − V_TD` and `V_FC − V_TD` in
  €/MW/day, on the main specification. Motivation: the capture-share ratio is noisy on
  near-zero-value days (the robustness table shows precision tracking the ratio floor),
  and the euro gap is the economically natural measure of value that needs information.
- **E2, a fixed denominator for the treatments.** Wind and solar forecast MWh divided by
  the zone-year's mean daily load forecast, instead of the same day's. Motivation: daily
  forecast load moves with temperature, itself weather, so part of the variation in
  penetration could come through the denominator.

## Corrections

**2026-09-27, found by the referee.** Deviation 4 is factually wrong in two places. There
are 1,204 zone-days with V* = 0 across 14 zones, not 609 in NO_2 alone, and none has
flat prices: V* = 0 means no intraday spread exceeded the 15% round-trip loss. The rule
itself is unchanged, since capture shares still require V* > 0 with the floor among
positive days, but it changes the floor in 14 zones, not one. log V* drops these days,
1,008 of them in the estimation sample, which the first draft did not disclose. Deviations
4 and 5 were also logged after V* had been computed, though before any regression. The
first draft said they predated every outcome.

**The registered 14-day typical-day check** was omitted from the first draft and has now
been run.

**2026-09-29, two further points from the referee.**

- The inference paragraph above says "19 clusters". Czechia left the regression sample
  (deviation 1), so every regression has 18.
- Deviation 3 says FC − TD is "the value of day-specific information exactly". It is
  not. A forecaster trained on squared price error need not dominate TD in arbitrage
  revenue, and ours does not beat it in four zones. FC − TD measures how much this one model
  extracts from the information, not what the information is worth.

The referee also requested further checks, all run after results were seen and all
reported as exploratory:

- terciles of K and the H4 interaction on FC − TD;
- a log load control and neighbours' forecast penetration;
- the typical-day operator's revenue in euros;
- equivalence tests for the forecast-error placebo;
- partial leverage by zone;
- Driscoll–Kraay standard errors.
