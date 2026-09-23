# Research design: the value of information in storage arbitrage

Written 2026-09-22, before the panel data was pulled, so the design is fixed before any
result can shape it. Changes after the data arrives are recorded at the foot of this file
with the reason, and are not made silently.

## The question

> **As electricity systems add weather-dependent generation, does more of the value of
> storage require information to capture?**

This replaces "does decarbonisation transfer storage value to sophisticated operators".
That earlier question mixed two effects, and the confusion between them is part of why the
section 5.6 claim failed.

1. **A scale effect.** Renewables make prices more volatile, and volatility is what storage
   earns from. Every operator's revenue rises in pounds, the naive one's included, so the
   gap between a sophisticated and a naive operator can widen in levels while the share of
   value each captures stays unchanged. That is interesting, but it is about how much
   storage is worth, not who captures it.
2. **An information effect.** Renewables change the *shape* of volatility: less
   clock-regular, more weather-driven. A time-of-day rule then captures a smaller share of
   the ceiling, and a forecasting operator a relatively larger one. This is the effect the
   question is really about.

The paper estimates both separately. Only the second supports a claim about who captures
the value.

**Why an economist would care.** Merchant revenue is the business case for grid storage,
and support schemes are sized on the assumption that it is captured. If a growing share
depends on forecasting, the returns favour operators with scale in data and trading. That
bears on market structure. It also gives the public value of TSO forecast quality, which
becomes an input to private storage revenue.

## Outcomes

For each zone *z*, day *d* and battery configuration:

| Symbol | Meaning |
| --- | --- |
| `V*` | Perfect-foresight MILP revenue: the ceiling |
| `V^N` | Fixed time-of-day rule: no information |
| `V^P` | Persistence: optimise on yesterday's prices, settle on today's (adaptive, zero skill) |
| `V^F` | Gradient-boosted forecast of day-ahead prices, optimised then settled on actual prices |

Every operator optimises over the day with the store empty at both ends, as in the GB
study. Revenue is in EUR/MW/day. Every panel zone prices in EUR (checked against the platform
with `entsoe --verify`), so no conversion is needed; `ref.zone.currency` records it.

**Primary outcomes:**

- `log V*` for the scale effect.
- Capture shares `V^k / V*` for the information effect.
- The premium `(V^F − V^N) / V*`, which is the object in the question.

Ratios are unstable on flat days, where `V*` is close to zero. Days with `V*` below the
zone's 5th percentile are excluded from the ratio regressions and kept in the level
regressions. The threshold is fixed here and reported with a sensitivity check. It is not
tuned.

**Aggregation rule** (proof under "Design notes" below): compute per zone, then average outcomes. Never
average prices before optimising. `V` is convex in the price vector, so pooling prices
first is biased toward zero. That bias was measured on GB data at 20% on average.

## Identifying variation

The earlier failures share one root cause: renewable *share* trends upward and moves
with everything else. Here it is split into two parts with very different exogeneity.

**1. A weather shock (exogenous, fast).** The treatment is the day-ahead forecast
capacity-factor anomaly:

    w_zd = (forecast wind + solar MW on d) / (installed wind + solar MW in z's year)
           − mean of the same for zone z in d's calendar month

This measures weather in physical units, separately from how much capacity a zone has
built. Nobody in the market chooses it. Conditional on zone-by-month fixed effects it is
plausibly as good as random, and date fixed effects remove the part shared across Europe.

**2. Installed capacity (endogenous, slow).** `K_zy` = wind + solar capacity divided by the
zone's mean load. Zones choose it, and it is correlated with policy, resources and market
design. It never enters as a treatment on its own. It enters only through its interaction
with weather.

**Main specification:**

    Y_zd = β₁ w_zd + β₂ (w_zd × K_zy) + γ K_zy + X_zd′δ + α_{z,moy} + λ_d + ε_zd

- `α_{z,moy}` are zone-by-month-of-year effects. They absorb each zone's permanent
  seasonal shape, including heating and cooling demand, holidays and the hydro cycle.
- `λ_d` are date effects. There are about 2,800 of them. They absorb everything common
  to Europe on a given day: the gas price, the carbon price, and continental weather
  systems in part.
- `X_zd` holds demand-shape controls built from the day-ahead load forecast: load factor
  and peak-to-trough range. These cover the time-varying demand heterogeneity that the
  fixed effects cannot.
- **β₂ is the estimand.** It asks whether the same weather shock matters more for the
  outcome in a system with more weather-dependent capacity. That is how decarbonisation
  changes the value of information, and the identifying variation comes from weather
  rather than from the trend.

**The strongest version** adds zone-specific slopes on `w` (`w_zd × α_z`). β₂ is then
identified only from *within-zone* capacity growth: "as zone *z* built turbines, did its
own sensitivity to weather rise?" If the result survives this, the cross-sectional
confounding objection no longer applies.

**Remaining threat to β₂.** Something else that changed alongside a zone's capacity
build-out could also change its weather sensitivity. The obvious candidates are
interconnection and market-design reforms. Interconnector capacity from ENTSO-E is the
control to add if the result is sensitive to this.

## Information sets and timing

The European day-ahead auction closes at 12:00 CET on D−1. An operator's forecast for day
*d* can use only what is known by then:

| Input | Available at gate closure? |
| --- | --- |
| Prices up to and including D−1 | Yes. D−1 cleared on D−2. |
| TSO day-ahead load forecast | Yes. Per Regulation 543/2013 it is published at least two hours before gate closure. |
| TSO day-ahead wind and solar forecast | **Not guaranteed.** The deadline is 18:00 on D−1, which is after gate closure. |
| Calendar features | Yes |

The wind and solar timing is a real caveat. Commercial operators run their own weather
forecasts, which are about as skilled as the TSOs' and ready before gate closure, so the
TSO series is a reasonable proxy for a competent operator's information. The paper states
that assumption and tests it. A **strict variant** uses only information guaranteed before
12:00. If the results hold under the strict variant, the caveat does not matter. If they
do not, that difference is itself a finding about the value of weather forecasts. The
regulation deadlines above should be checked against the regulation text before the paper
cites them.

## Inference

There are 21 zones, which is too few for standard cluster-robust errors to be trusted.
Planned approach:

- The main tables use two-way clustering by zone and by date.
- Key coefficients also get wild cluster bootstrap p-values at zone level (Rademacher
  weights, 9,999 draws).
- Driscoll-Kraay errors are a robustness check against cross-sectional dependence, since
  neighbouring zones share weather.

## Supporting designs

1. **Iberian exception, June 2022.** This is a clean difference-in-differences: ES and PT
   are treated, the rest of the panel is the control, and the treatment was a regulated
   cap on the gas price used for power. It tests whether a change in how prices form
   shifts the ceiling and the capture shares. It has a real date and real treated and
   control groups, so it is an actual DiD, and a good one. It is presented as evidence
   about price formation, not as the answer to the main question.
2. **Incumbent storage.** Zones with deep pumped-storage fleets (CH, AT, NO_2) should show
   compressed ceilings, because the arbitrage is already being done. This is descriptive
   and cross-sectional. It is reported as heterogeneity, not as a causal claim.
3. **Pipeline validation.** GB appears on both the Elexon and ENTSO-E sides. Replicating
   the GB result on ENTSO-E day-ahead data tests both pipelines. GB publication on the
   platform may have thinned after GB left ENTSO-E in 2021, so the overlap could be short.
   That will be clear from the pull.

## What gets reported

- **Table 1.** Descriptives by zone: VRE share, K, ceiling, and the capture share of each
  operator.
- **Table 2.** The main specification with a staged build-up of fixed effects: none, then
  zone, then zone-by-month, then date, then zone slopes. It shows exactly where each
  earlier false positive would have come from.
- **Table 3.** Scale effect versus information effect side by side.
- **Table 4.** The strict information set against the TSO-forecast information set.
- **Figure 1.** Binned scatter of the capture-share premium against the weather anomaly,
  split by terciles of K.
- **Figure 2.** Iberian event study with leads and lags.
- **Appendix.** Battery durations of 1h, 2h and 4h; the ratio-floor sensitivity; and
  leave-one-zone-out estimates.

## What would falsify it

- **β₂ indistinguishable from zero in the zone-slope specification.** The honest reading
  would be that renewables raise the value of storage (the scale effect) without changing
  who captures it. That result is publishable, and it contradicts a common assumption.
- **The strict and TSO-forecast variants diverge sharply.** The result would then be about
  weather forecasts rather than price forecasts, and the paper would be reframed around
  that.

## Scope honesty

- This is the day-ahead market only. Real batteries earn most of their revenue in
  balancing and ancillary services. The paper's claim is about the energy-arbitrage
  component, and it says so.
- Operators are price-takers. That holds for one battery, not for the fleet.
- A proper literature review is still owed. The anchor is Sioshansi, Denholm, Jenkin and
  Weiss (2009, *Energy Economics*) on arbitrage value in PJM. Other citations should be
  added from actual reading rather than from memory.

## Design notes

Arguments settled while designing the panel. They are recorded here because each answers
an objection a reader or referee will raise, and each was checked rather than asserted.

### This is not textbook difference-in-differences

Renewable share is continuous and rises everywhere, so there is no treated/control split
and no single treatment date. The panel supports two-way fixed effects with a continuous
regressor, identified from within-zone deviations relative to other zones in the same
period. That is a real improvement on the GB series, which had no control for common
shocks at all, but two caveats hold before anything is run:

1. **TWFE with a continuous, staggered, heterogeneous treatment is badly behaved.** Where
   effects differ across units and time, the estimator can put negative weight on some
   comparisons. A headline resting on TWFE alone should be checked against a modern
   estimator before it is believed.
2. **Renewable capacity is not randomly assigned.** That is why the main specification
   identifies from weather anomalies and lets capacity enter only through an interaction.

The Iberian exception is the one genuine DiD available: it has a real date, a treated
group and a control group.

### Aggregate outcomes, never prices

`ref.zone.country_code` allows national reporting, but the aggregation must happen on the
**outcome**, after each zone's battery model has run, and never on the price before it.
The perfect-foresight optimum `V(p) = max {p'x : x in X}` is a pointwise maximum of linear
functions of the price vector, so it is convex in `p` for any feasible set, the MILP's
non-convex one included. By Jensen's inequality, `V(mean(p1, p2)) <= mean(V(p1), V(p2))`.

Measured on 199 random pairs of real GB 2023 days, 50 MW / 2h at 85% round-trip: zero
violations, **19.9% mean understatement, 59.8% on the worst pair.** The bias is toward the
null on this project's question, and it is worst in the zones with the most internal price
separation, which are the high-renewable ones. So compute per zone, then average the
results, load-weighted.

### Bidding zones rather than countries, and national heterogeneity

Price forms at zone level: DK1 and DK2 are on different synchronous areas and clear apart
on most days. Zone fixed effects are strictly finer than country fixed effects, so
disaggregating cannot add omitted-variable bias relative to aggregating. Permanent national
patterns (holidays, heating stock, industrial mix) are absorbed by construction.

What zone effects do **not** absorb is time-varying heterogeneity:

- **Demand-shape trends:** air conditioning in ES and GR, heat pumps and EVs in the Nordics,
  and the 2022 saving mandates. Control for these directly with load factor and
  peak-to-trough range built from `entsoe.load_forecast`.
- **Market-design changes,** which are the stronger objection: gate closure, intraday
  markets, XBID, imbalance pricing, interconnection, and the 15-minute market time unit in
  2025. These bear directly on what a forecast is worth.

### Known data limits that shape the sample

- DE and AT shared a bidding zone until 2018-10-01, so the panel starts in 2019.
- GB leaves ENTSO-E's coverage in 2020–21, so it is a cross-check, not a panel zone.
- IE_SEM has almost no load forecast after mid-2021. Drop it from forecast-based
  specifications.
- Reported capacity is clean for only 16 zones. The generation-based proxy (annual 99th
  percentile of hourly wind plus solar) applies one definition everywhere, with reported
  capacity as a robustness check.

## Changes after data

*None yet.*
