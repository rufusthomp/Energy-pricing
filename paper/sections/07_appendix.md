# References {-}

::: {#refs}
:::

\newpage
\appendix

# Pre-registration, deviations and revision record

## Registration

All hypotheses, the specification, the sample, the outcome definitions and the
robustness set were fixed in a pre-registration document committed to the project's
version control before any panel backtest had run (commit `6aa7cdc`, 27 September 2026).

| | Outcome | Registered prediction | Result |
| --- | --- | --- | --- |
| H1 | Typical-day capture | $\beta_w < \beta_s$ | Predicted sign; not significant (WCB p = 0.120) |
| H2 | Shape novelty | $\beta_w > 0$ and $\beta_w > \beta_s$ | Holds (p < 0.001), with the placebo caveat in Section 6 |
| H3 | $\log V^*$ | No direction registered | Solar raises $V^*$; wind does not |
| H4 | Typical-day capture | Wind effect more negative where wind is a larger share | Holds in the full sample, but driven by DK_1 alone |
| Placebo | All of the above | Forecast-error coefficient zero | Fails for novelty; elsewhere too imprecise to be informative |

The registered hypothesis text also predicted that wind would "raise [arbitrage value],
or reshape it". Wind does not raise value (Table 6), so that part of the hypothesis failed.

## Deviations

Five deviations were logged before the first regression was estimated. Deviations 4 and 5
were logged after the ceiling $V^*$, which is an outcome, had been computed and inspected
in summary statistics. The first draft said all deviations predated every outcome, which
was not accurate for these two.

1. **Czechia leaves the regression sample.** It publishes no day-ahead wind forecast.
2. **The gas-crisis window is fixed at 1 July 2021 to 30 June 2023.** The registration
   named the check but not its dates.
3. **The forecaster predicts deviations from the typical-day profile, not price levels.**
4. **Capture shares require $V^* > 0$,** with the 5th-percentile floor computed among
   positive days. As logged, this deviation wrongly stated that only NO_2 has zero-value
   days and that its prices are flat on them. In fact 1,204 zone-days across 14 zones have
   $V^* = 0$, and none has flat prices. The rule is unchanged; its description is
   corrected, and it changes the floor in 14 zones, not one.
5. **Implausible load forecasts are set to missing.** These are days outside 50–200% of
   the zone's median for the month. The rule affects 11 days.

## Revision after review

A referee report on the first draft identified the following. Each was addressed as
described.

- **A bootstrap implementation error.** Each draw's outcome was not re-projected off the
  fixed effects. Date effects cross the zone clusters, so this understated every
  wild-bootstrap p-value. H1's p-value moves from 0.099 to 0.120. The corrected code
  reproduces the referee's replication exactly.
- **Overclaiming.** The first draft's title, abstract and conclusion presented H1 as
  supporting a claim that solar-created value is "public" and wind-created value
  "informational". The value-of-information outcomes added in revision (Table 7) contradict
  the wind half of that claim, so it has been removed.
- **A missing registered check.** The 14-day typical-day window is now reported
  (Table 5).
- **Factual errors** about zero-value days, the fixed-effect structure (additive, not
  zone×year×month), the CET offsets, and the Figure 1 discussion have been corrected.
- **Identification checks added at the referee's request,** all exploratory:
  - region×date and zone×year×month fixed effects;
  - a fixed load denominator;
  - excluding negative-price days;
  - a pre-15-minute-MTU sample;
  - a lead placebo;
  - rank-based novelty and timing measures;
  - H4 without the Danish zones;
  - jackknife standard errors and exact Rademacher enumeration.
- **Two forecaster feature bugs.** A rolling window counted rows rather than calendar
  days, and daily shares summed partial-coverage days. Neither leaked future information.
  Both were fixed and the forecaster re-run.
- **Literature** was added on intraday price shape, weather-based identification and
  cluster-robust inference. Each reference was verified before being cited.

**Why the design is built this way.** An earlier single-market analysis of this question
on British data reported that decarbonisation shifts storage value towards sophisticated
operators. That claim did not survive the addition of year fixed effects. The current
design responds in three ways:

- identification comes from day-to-day variation within zone-years;
- the treatments are forecasts;
- the specification was fixed in advance.

The review of this paper found an error of a different kind, in the inference rather than
the specification. That is why the code, data and review are all part of the record.

# Operator details

**The optimisation.** All operators solve the same mixed-integer programme with the HiGHS
solver through SciPy, on the price vector their information set provides. The schedule is
then settled at actual prices. The panel required approximately 700,000 solves with no
solver failures. Each schedule was checked against the physical limits on state of charge
and power before being recorded.

**The forecaster.** For each zone, a histogram gradient-boosted regression tree
predicts, for every hour of day $d$, the price's deviation from the typical-day profile.
Its features are:

- the market hour, weekday and month;
- the typical-day price for that hour;
- yesterday's price at that hour and yesterday's mean, each as a deviation from the
  profile;
- the TSO's day-ahead forecasts of load, wind and solar for that hour, each also expressed
  relative to its mean over the previous 28 calendar days;
- the day's forecast wind and solar shares of load, defined only when the forecasts cover
  every hour.

The model is refitted monthly on an expanding window, and it forecasts only months
strictly after its training data. Germany-Luxembourg's zone begins only in October 2018,
and the first model needs 180 days of training, so its forecasts begin on 1 May 2019.

**Reproducibility.** Every table, figure and quoted number is produced by code in the
project repository from the raw ENTSO-E data, and the paper is compiled from those
outputs:

    python -m gbmo.ingest.entsoe && python -m gbmo.ingest.load_zones
    python -m gbmo.arbitrage.panel && python -m gbmo.arbitrage.panel --td14
    python -m gbmo.arbitrage.panel_forecast
    python -m gbmo.analysis.panel_data && python -m gbmo.analysis.results
    python paper/build.py
