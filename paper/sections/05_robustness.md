# Robustness and limitations

## Placebos

**The registered forecast-error placebo.** The day-ahead auction clears before the wind
forecast error is realised, so the error should not affect any day-ahead outcome. Table 7
adds realised minus forecast wind to the main specification.

{{table:t07_placebo|Placebos: the realised wind forecast error, and the next day's forecasts.}}

The placebo fails for shape novelty. The error coefficient is 0.009 per 10 pp
(p = 0.015), about two-thirds of the forecast coefficient. Elsewhere it does not reject,
but that is weak evidence. The error coefficients are imprecise enough that the
equivalence tests in Table 7 cannot show them to be smaller than the forecast effects
they are meant to benchmark (equivalence p-values run from 0.06 to 0.43, so none establishes equivalence at 5%). For the spread, the error coefficient
(−2.53) is as large as the forecast coefficient (−2.96).

Two readings of the novelty failure fit the data, and we cannot separate them. Market
participants trade on their own weather forecasts, so the TSO's error may partly proxy for
information the market had. Or large forecast errors may occur on frontal and transition
days whose price shapes are atypical for reasons the market knew. Either way, the wind
coefficient on novelty should not be read as the effect of the published forecast alone.
With fixed effects and two correlated, mismeasured regressors, the direction of any bias
in the other coefficients is not signed.

**The next day's forecasts (exploratory).** We added the next day's forecast penetration
as a second placebo, on the premise that it cannot affect day $d$'s auction. That premise
is wrong, and the test is informative for that reason. Weather forecasts for $d+1$ exist
when day $d$'s auction clears. Reservoir hydro and multi-day unit commitment make prices
respond to anticipated wind. Tomorrow's wind forecast predicts today's typical-day
capture (−1.57, p = 0.002), today's value (−0.040, p < 0.001) and today's novelty
(+0.016, p < 0.001). Tomorrow's solar forecast predicts almost nothing.

Table 8 uses the lead as a control instead. Within the fixed effects, today's and
tomorrow's wind forecasts correlate at 0.50. Holding tomorrow fixed leaves every solar
coefficient essentially unchanged: 0.243 for log $V^*$ and −0.050 for novelty. It cuts
the wind coefficient on novelty from 0.013 to 0.005 (p = 0.19). Solar acts on the day.
Much of wind's effect on the day's shape belongs to multi-day weather regimes, which is
also consistent with the novelty placebo's failure.

{{table:t08_lead|Today's effects, holding tomorrow's forecasts fixed (exploratory).}}

## Robustness of the registered test

Table 9 reports the registered robustness set for H1 and, marked †, the exploratory
checks the referee requested. We present them in full, without selecting.

{{table:t09_robustness|Robustness of the key estimate (typical-day capture).}}

- **Point estimates** of $\beta_w - \beta_s$ range from −3.54 (region×date effects) to
  −6.89 (zone×year×month effects). All have the predicted sign.
- **p-values** range from 0.003 to 0.296. Among the registered checks, three are below
  0.10 (the 1-hour battery, the 10th-percentile floor and excluding the gas crisis), and
  four are not (the 4-hour battery, the 14-day window, the 1st-percentile floor and two-way
  clustering).
- **Leave-one-zone-out estimates** range from −3.08 (without Poland) to −6.45 (without
  NO_2). This is weak evidence of stability, since every pair of estimates shares 16 of
  18 clusters.

Some variants are more precise for reasons unrelated to the sign. Excluding the gas crisis
removes 28% of zone-days yet cuts the standard error by 37%, which shows that crisis days
are high-leverage in the ratio. Nothing in Table 9 changes the registered verdict: the
sign is as predicted, and the test is inconclusive.

![Leave-one-zone-out estimates of $\beta_w - \beta_s$ for typical-day capture, with 95%
confidence intervals from zone-clustered standard errors. The dashed line is the
full-sample estimate.](figures/f4_leave_one_out.pdf){width=95%}

**Inference.** Eighteen clusters of unequal influence are the setting in which
cluster-robust inference is least reliable [@mackinnonwebb2017; @mackinnon2023]. Table 10
reports each zone's partial leverage. For wind, Denmark West contributes a third of the
identifying variation. For solar, the largest share is Greece's, at 15%. NO_2 has no solar
at all, yet it contributes 2.4% of the solar variation, because date effects
turn its zeros into deviations from other zones' sunny days. We therefore report three
p-values for H1, and they agree: 0.120 (Webb WCB), 0.147 (CV3 jackknife) and 0.116 (exact
Rademacher enumeration). Two-way clustering by zone and date gives a slightly *smaller*
standard error (2.52 against 2.59). Driscoll–Kraay standard errors, which allow any
dependence across zones on the same day, are much smaller still (0.86 with a 7-day lag and 0.97 with a 28-day lag, against 2.59). They
allow serial dependence only within a lag window, however, and zone-level persistence
beyond it is exactly what zone clustering protects against. We do not rely on them.

{{table:t10_leverage|Partial leverage of each zone (exploratory).}}

## Robustness of the scale result

Table 11 (exploratory) subjects "solar raises $V^*$" to the same checks. The coefficient
ranges from 0.148 (region×date effects) to 0.293 (a fixed load denominator), and every
p-value is below 0.01. It survives excluding the roughly 10% of zone-days with a negative
price hour, which rules out the concern that solar raises $V^*$ only by producing
negative prices a battery is paid to absorb. Wind is not significant at 5% in any row.

{{table:t11_scale|Robustness of the effect on arbitrage value (exploratory except the first row).}}

## Threats to identification

**The fixed effects are additive.** Zone×month effects are held fixed from 2019 to 2026,
so they cannot absorb a solar seasonal amplitude that grows with installed capacity.
Replacing them with zone×year×month effects moves every solar coefficient *away* from
zero (Tables 9 and 11). The additive specification is conservative here, but it is also
fragile to this natural refinement.

**Market coupling.** Date effects remove only what is common to all 18 zones. Part of the
identifying variation therefore compares different regions on the same day, for example
sunny Iberia against a cloudy, hydro-priced Nordic region. Those regions differ in
marginal technology, interconnection and congestion as well as weather. Region×date
effects compare each zone only with its own coupling region. They cut the solar
coefficient on log $V^*$ by about 40%, to 0.148 (p = 0.009), and H1 to −3.54 (p = 0.29).
Coupling also violates the stable-unit assumption, because a zone's price responds to its
neighbours' weather [@lago2018]. Adding the neighbours' mean forecast penetration as a
control (the solar coefficient on log $V^*$ moves from 0.252 to 0.231 on the common sample, and the wind coefficient on novelty from 0.013 to 0.012; Table 12) does not change the conclusions. The coefficients
are best read as the effect of a zone's own weather given its neighbours', estimated
partly from comparisons across regions.

{{table:t12_identification|Load and spillover controls (exploratory).}}

**The denominator moves with weather.** Penetration is forecast output over forecast
load, and forecast load itself falls on sunny days (-0.045 log points per 10 pp of solar, s.e. 0.007). Some TSOs net
embedded solar out of their load forecasts, and temperature moves load. We have not
established which TSOs do so. A fixed denominator (the zone-year's mean load) and a log
load control both leave the results intact or stronger (Tables 9, 11 and 12).

**Forecast timing.** Regulation 543/2013 requires TSO wind and solar forecasts by 18:00
on D−1, six hours after the auction. A published forecast may therefore contain updates
the auction did not have, and some TSOs' renewable forecasts may be net of expected
curtailment at negative prices, which would make the treatment partly a function of the
price. We did not recover publication timestamps. Excluding negative-price days leaves
the results unchanged (Tables 9 and 11), but the timing question is open. Instrumenting
with numerical-weather-prediction or reanalysis weather would resolve it.

## Limitations

**Day-ahead only.** Batteries earn much of their revenue in intraday, balancing and
ancillary-service markets, which we do not model. Intraday markets are where forecast
errors are traded, so any informational premium to wind is more likely to appear there.

**Price-taking and daily independence.** The battery does not move prices, which suits
one battery and not a fleet [@butters2025; @karaduman2023]. Each day starts and ends
empty, which forgoes multi-day arbitrage. That understates value most for the four-hour
battery and in hydro-dominated zones.

**One forecaster.** The forecaster is one reasonable gradient-boosted model trained on
squared error, not the frontier [@lago2021], and not a decision-focused model. A
forecaster tuned for rank accuracy, which drives capture [@falezza2026], might gain more
on windy days. Our value-of-information results bound what this model extracts, not what
the information is worth.

**Heterogeneity is descriptive.** Comparisons across systems by wind share confound wind
capacity with everything else that differs between those systems, and our one clear case
is a single zone.
