# Robustness and limitations

## The forecast-error placebo

The day-ahead auction clears before the forecast error is realised, so the error should
not affect any day-ahead outcome. Table 4 adds realised minus forecast wind to the main
specification.

- **The placebo passes for capture, value and spread.** The error coefficient is
  0.05 for typical-day capture (WCB p = 0.91), −0.003 for log V* (p = 0.89) and −2.5 for
  the spread (p = 0.28). This supports the timing of the data, and it supports the claim
  that these outcomes respond to what was known when the auction cleared.
- **It fails for shape novelty.** The error coefficient is 0.009 per 10 pp
  (p = 0.014), comparable in size to the forecast coefficient of 0.013.

{{table:t4_placebo|Placebo: the realised forecast error in wind.}}

The failure has a natural interpretation, and it qualifies the wind-novelty result.
Market participants trade on their own weather forecasts, not only the TSO's. When
realised wind exceeds the TSO forecast, commercial forecasts will often have anticipated
part of the excess. So the error is partly a proxy for information the market had and
our regressor lacks. On this reading, the TSO forecast measures the market's
information with error. The wind-novelty coefficient then reflects wind weather broadly,
including the part the TSO failed to forecast, rather than the TSO forecast narrowly.
The *direction* of the result, that windy weather makes a day's shape less typical, is
unaffected, since the forecast and its error act in the same direction. But its
magnitude should not be read as the effect of the published forecast alone. The
measurement-error interpretation also implies that the wind coefficients elsewhere in
Table 2 are, if anything, attenuated.

## Pre-registered robustness

Table 5 reports every robustness check fixed in the pre-registration, for the key
outcome.

{{table:t5_robustness|Robustness of the key estimate (typical-day capture).}}

**The point estimate of $\beta_w - \beta_s$ is stable across every specification**, from
−4.36 to −5.18 points per 10 pp. It holds across battery durations of one, two and four
hours, across ratio floors, and after excluding the 2021–23 gas crisis.

**Precision is not stable, and the reason is informative.** The estimate is sharpest
where the ratio outcome is least noisy:

- Excluding the gas crisis gives p = 0.008.
- A 10th-percentile floor on the ceiling gives p = 0.029.
- A 1st-percentile floor, which admits more near-zero-value days whose capture ratios
  are erratic, gives p = 0.26.

Two-way clustering by zone and date barely changes the standard error (2.52 against
2.59). That suggests residual cross-sectional correlation on a given day is not driving
inference.

The leave-one-zone-out estimates in Figure 6 range from −3.08 (without Poland) to −6.45
(without Norway). No single zone drives the sign. Norway's reservoir-hydro zone
contributes most of the imprecision. Without it, the estimate is −6.45 with a standard
error of 1.44. Norway has no solar, so it identifies only the wind coefficient, and its
near-flat prices make its capture ratios the noisiest in the panel.

We do not promote any of these variants to the headline. The pre-registered estimate is
the baseline, and it is marginal. What the robustness exercise shows is that its
magnitude is not an artefact of any one choice, and that its imprecision comes from
ratio noise on low-value days rather than from fragility in the sign.

![Leave-one-zone-out estimates of $\beta_w - \beta_s$ for typical-day capture, with 95%
confidence intervals from zone-clustered standard errors. The dashed line is the
full-sample estimate.](figures/f4_leave_one_out.pdf){width=95%}

## Limitations

**Day-ahead only.** Batteries in practice earn much of their revenue in intraday,
balancing and ancillary-service markets, which this paper does not model. Our results
concern the day-ahead arbitrage component. Intraday markets are where forecast errors
are traded, so the informational content of wind may be larger there than here. That is
the natural extension.

**Price-taking and daily independence.** The battery does not move prices, which is
appropriate for one battery and not for a fleet [@butters2025; @karaduman2023]. Each day
starts and ends empty, which forgoes multi-day arbitrage. That understates value most
for the four-hour battery and in hydro-dominated zones.

**Forecast timing.** Regulation requires TSO wind and solar forecasts by 18:00 on D−1,
after the 12:00 auction. The forecaster's information set is therefore mildly optimistic.
That caveat touches only the forecaster operator. The typical-day and persistence
operators use prices alone. The treatments are regressors rather than operator inputs,
so this timing issue does not affect them.

**Market coupling.** Coupled zones' prices respond to their neighbours' weather
[@lago2018]. Date fixed effects remove the Europe-wide component of weather, but not
regional spillovers. Our coefficients are best read as the effect of wind or solar
weather in a zone's region.

**Few clusters.** Eighteen zones is a moderate number of clusters. We use the wild
cluster restricted bootstrap with Webb weights throughout [@webb2023], but inference at
this cluster count remains less reliable than with many.

**One forecaster.** The forecaster is one reasonable gradient-boosted model, not the
frontier of price forecasting [@lago2021]. Its capture is a lower bound on what
day-specific information is worth.

**Heterogeneity is descriptive.** The finding that wind's cost grows with wind's share
(Section 5.5) compares systems that differ in many ways besides wind capacity. It does
not identify the causal effect of adding capacity.
