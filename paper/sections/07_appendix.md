# References {-}

::: {#refs}
:::

\newpage
\appendix

# Pre-registration and deviations

All hypotheses, the specification, the sample, the outcome definitions and the
robustness set were fixed in a pre-registration document committed to the project's
version control before any panel backtest had run (commit `6aa7cdc`, 27 September
2026). The registered hypotheses were:

| | Outcome | Prediction |
| --- | --- | --- |
| H1 | Typical-day capture | $\beta_w < \beta_s$ |
| H2 | Shape novelty | $\beta_w > 0$ and $\beta_w > \beta_s$ |
| H3 | $\log V^*$ | No directional prediction |
| H4 | Typical-day capture | The wind effect is more negative where wind is already a larger share |
| Placebo | All of the above | The forecast-error coefficient is zero |

Five deviations were recorded in the pre-registration's log. Each was recorded before the
first regression was estimated.

1. **Czechia leaves the regression sample.** It publishes no day-ahead wind forecast, so
   wind penetration is undefined. Imputing zero would invent data.
2. **The gas-crisis window is fixed at 1 July 2021 to 30 June 2023.** The registration
   named the robustness check but not its dates.
3. **The forecaster predicts deviations from the typical-day profile, not price levels.**
   It therefore nests the typical-day operator, and tree ensembles cannot extrapolate
   levels outside their training range.
4. **Capture shares require $V^* > 0$.** NO_2 has 609 days with perfectly flat prices,
   on which a share is undefined rather than zero. The 5th-percentile floor is computed
   among positive days. This changes the floor only for NO_2.
5. **Implausible load forecasts are set to missing.** These are days where the forecast
   is outside 50–200% of the zone's median for that month. The rule flags 11 days, all
   reporting errors.

**Outcomes against predictions.**

- **H1:** correct sign, marginal (p = 0.099).
- **H2:** holds, p < 0.001.
- **H3:** solar raises $V^*$ and wind does not.
- **H4:** holds, p = 0.02.
- **Placebo:** passes for three of four outcomes and fails for novelty, as discussed in
  Section 6.1.

**Why the design was built this way.** An earlier, single-market analysis of the same
question on British data had reported that decarbonisation shifts storage value towards
sophisticated operators. That claim did not survive the addition of year fixed effects.
Renewable penetration and forecaster capture both trended upward over the sample, and
the specification could not separate them. The current design rules that failure out in
three ways:

- identification comes from weather within zone-years, so no common trend can load onto
  the treatment;
- the treatments are forecasts, which is the information on which the auction clears;
- the specification was fixed before the data were examined.

# Operator details

**The optimisation.** All operators solve the same mixed-integer programme, with the
HiGHS solver through SciPy, on the price vector their information set provides. The
schedule is then settled at actual prices. The panel required approximately 640,000
solves (19 zones × 3 durations × 4 operators × about 2,800 days) with no solver failures.
Each schedule was checked against the physical limits on state of charge and power
before being recorded.

**The forecaster.** For each zone, a histogram gradient-boosted regression tree
predicts, for every hour of day $d$, the deviation of the price from the typical-day
profile. Its features are:

- the market hour, weekday and month;
- the typical-day price for that hour;
- yesterday's price at that hour and yesterday's mean, each as a deviation from the
  profile;
- the TSO's day-ahead forecasts of load, wind and solar for that hour, and each relative
  to its own 28-day mean;
- the day's forecast wind and solar shares of load.

The model is refitted monthly on an expanding window of all earlier days, and it
forecasts only months strictly after its training data. The first forecasts use models
trained on 2018. Germany-Luxembourg's zone begins only in October 2018, and the first model needs 180
days of training, so its forecasts begin on 1 May 2019.

**Reproducibility.** Every table, figure and quoted number is produced by code in the
project repository, from the raw ENTSO-E data, and the paper is compiled from those
outputs:

    python -m gbmo.ingest.entsoe && python -m gbmo.ingest.load_zones
    python -m gbmo.arbitrage.panel && python -m gbmo.arbitrage.panel_forecast
    python -m gbmo.analysis.panel_data && python -m gbmo.analysis.results
    python paper/build.py
