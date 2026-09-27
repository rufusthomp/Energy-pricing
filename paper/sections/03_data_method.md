# Data and design

## Market data

All market data come from the ENTSO-E Transparency Platform, which publishes standardised
data for European bidding zones under Commission Regulation (EU) No 543/2013. We use five
series at hourly resolution for 2019-01-01 to 2026-09-20:

- day-ahead clearing prices;
- actual total load;
- actual generation by production type;
- the transmission system operators' (TSOs') day-ahead load forecasts;
- the TSOs' day-ahead forecasts of wind and solar generation.

The unit of observation is the **bidding zone**, not the country, because day-ahead
prices clear at zone level. Denmark's two zones sit on different synchronous areas and
frequently clear at different prices.

The operators are run on 19 zones spanning the range of European generation mixes:

| Group | Zones |
| --- | --- |
| Nordic and Baltic | DK_1, DK_2, NO_2, SE_3, SE_4, FI, EE |
| Central-western | DE_LU, NL, BE, FR, AT, CH, CZ, PL |
| Iberian | ES, PT |
| Southern | GR, IT_NORD |

Great Britain is excluded because the platform holds no GB day-ahead prices after 2020.
Ireland (SEM) is excluded because its load forecast is almost entirely absent after
mid-2021. Czechia publishes no wind forecast, so its wind penetration is undefined and it
drops out of every regression. **All regressions therefore use 18 zones.** Czechia remains
in the descriptive statistics.

Two features of the data require care:

- **Resolution.** From October 2025 the day-ahead auction moved to a 15-minute market
  time unit in most zones. We average quarter-hours into hours, which is the price a
  battery holding a flat position over the hour receives.
- **The trading day.** Every coupled zone trades a *delivery day* defined on Central
  European Time, including zones whose civil time differs. Because EU daylight saving is
  synchronised, Portugal's trading day begins at 23:00 local time all year, and Finland's,
  Estonia's and Greece's at 01:00. We verified this against the platform's own price
  documents. Every "day" in this paper is a CET delivery day: 24 hours, or 23 or 25 on
  clock-change days.

## Treatment variables

Our treatments are the TSOs' day-ahead forecasts. For zone $z$ and delivery day $d$:

$$
\text{wind}_{zd} = 100 \times \frac{\sum_{h \in d} \widehat{W}_{zh}}{\sum_{h \in d} \widehat{L}_{zh}},
\qquad
\text{solar}_{zd} = 100 \times \frac{\sum_{h \in d} \widehat{S}_{zh}}{\sum_{h \in d} \widehat{L}_{zh}},
$$

where $\widehat{W}$, $\widehat{S}$ and $\widehat{L}$ are forecast wind output, solar
output and load in MWh. A penetration is defined only when the forecasts cover every hour
of the day and the load forecast is plausible. Eleven days, all reporting errors, fall
outside 50–200% of the zone's median for their month and are excluded.

The TSO forecast is a proxy for the information on which the auction clears, not a
measure of it. Commercial participants use their own forecasts. The regulation also
requires wind and solar forecasts only by 18:00 on D−1, six hours after the 12:00
auction, so a published forecast may contain updates the auction did not have. Two
further features of the construction matter for interpretation (Section 6):

- the load denominator itself falls on sunny days;
- the treatments are compared across regions on the same day.

## Arbitrage operators

We model a price-taking battery with 1 MW of power, 2 MWh of energy and 85% round-trip
efficiency. Batteries of one and four hours are robustness checks. Each day it starts and
ends empty, which makes days independent and comparable. For any price vector
$\boldsymbol{\pi} = (\pi_1, \ldots, \pi_H)$ over the $H$ hours of a day, the schedule
solves the mixed-integer linear programme

$$
\max_{c, s, e, z} \; \sum_{h=1}^{H} \pi_h (s_h - c_h)
\quad \text{s.t.} \quad
e_h = e_{h-1} + \sqrt{\rho}\, c_h - s_h / \sqrt{\rho},\;
0 \le e_h \le \bar{E},\;
0 \le c_h \le \bar{P} z_h,\;
0 \le s_h \le \bar{P}(1 - z_h),\;
e_0 = e_H = 0,
$$

with $c$ charging and $s$ discharging power, $e$ the stored energy, $\rho$ the round-trip
efficiency, and binary $z_h$ preventing simultaneous charging and discharging. The
binaries are necessary rather than cosmetic. At negative prices, charging and
discharging at the same time is strictly profitable in the linear relaxation, because it
burns energy the operator is paid to take.

The operators differ only in the price vector they optimise against. Each schedule is
then settled at the day's actual prices.

| Operator | Optimises against | Information used |
| --- | --- | --- |
| Perfect foresight (PF) | Actual prices of day $d$ | The ceiling, $V^*_{zd}$ |
| Typical day (TD) | Mean price by market hour over days $d-28$ to $d-1$ | The recent calendar shape |
| Persistence (PS) | Day $d-1$'s prices, by market hour | Yesterday |
| Forecaster (FC) | TD profile plus a gradient-boosted correction | TD's set, plus TSO day-ahead load, wind and solar forecasts |

For TD, at least 20 of the 28 days must be complete. TD and PS use only prices known at
gate closure: day $d-1$ cleared on $d-2$. FC is refitted monthly on an expanding window,
and its wind and solar inputs carry the 18:00 timing caveat above (details in Appendix B).
Because every operator shares one optimiser, differences between them reflect
information and how it is used.

For FC this is a statement about one model, not about the information itself. A forecaster
trained on squared error need not dominate TD in arbitrage revenue, and it does not in four
zones. So FC − TD measures how well this model uses day-specific information, not what
that information is worth. Rules that dispatch on recent historical prices are a natural
benchmark, and we claim no novelty for TD itself. Our interest is in how its performance
varies with the renewable mix.

## Outcomes

- **Capture shares**, $100 \times V^{k}_{zd}/V^*_{zd}$, for each operator. They are
  defined only where $V^* > 0$ and $V^*$ is at or above the zone's 5th percentile of
  positive values. $V^* = 0$ does not mean flat prices. It means no intraday spread
  covered the 15% round-trip loss, which happens on 1,204 zone-days across 14 zones, 609
  of them in NO_2.
- **Scale:** $\log V^*$ (registered). It drops the zero-value days, so we also report
  $\log(1+V^*)$ and $V^*$ in euros.
- **Mechanism:**
  - *Shape novelty*, $1 - \operatorname{corr}(\boldsymbol{\pi}_d, \bar{\boldsymbol{\pi}}^{TD}_d)$
    (registered);
  - a rank-correlation version, and the hour distances between the day's actual and
    typical maximum and minimum (exploratory), which separate timing from amplitude;
  - the daily spread, $\max_h \pi_h - \min_h \pi_h$.
- **Value of information** (exploratory): the value each operator leaves on the table in
  euros, $V^* - V^{k}$, and the forecaster's gain over the calendar, $V^{FC} - V^{TD}$.
  These avoid the capture share's near-zero denominators.

# Empirical strategy

We estimate

$$
Y_{zd} = \beta_w\, \text{wind}_{zd} + \beta_s\, \text{solar}_{zd}
+ \alpha_{z,y(d)} + \gamma_{z,m(d)} + \lambda_d + \varepsilon_{zd}.
\tag{1}
$$

The fixed effects are additive:

- **zone-by-year**, $\alpha_{z,y}$, absorbing capacity build-out, market reforms and
  zone-specific trends;
- **zone-by-month-of-year**, $\gamma_{z,m}$, absorbing each zone's average seasonal cycle;
- **date**, $\lambda_d$, absorbing everything common to all zones on a day, such as gas
  and carbon prices.

The identifying variation is a zone's day-to-day deviation from its year level and
average seasonal profile, relative to the other zones on the same day. Two things follow
from that description. The effects are additive, so a solar season whose amplitude grows
with installed capacity is not fully absorbed; we report zone×year×month effects as a
check. And date effects remove only what is common to *all* zones, so part of the
variation compares different regions on the same day. We therefore also report
region×date effects, which compare each zone only with its own neighbours.

We describe the variation as driven by weather, with the caveats set out in Section 6.

**The registered test (H1)** is $\beta_w < \beta_s$ for typical-day capture. We
re-parameterise (1) with $\text{wind}_{zd}$ and $\text{vre}_{zd} = \text{wind}_{zd} +
\text{solar}_{zd}$ as regressors, so the coefficient on wind is $\beta_w - \beta_s$.

**Inference.** Errors are clustered by zone. With 18 clusters, conventional
cluster-robust inference over-rejects [@cameron2008; @mackinnonwebb2017], so key p-values
come from a wild cluster restricted bootstrap with Webb six-point weights [@webb2023] and
9,999 draws. The date effects are not nested within the zone clusters, so each bootstrap
draw re-projects the reweighted residuals off the fixed effects. An earlier version of our
code omitted that step, which understates p-values. It was corrected after review
(Appendix A). For the key test we also report jackknife (CV3) standard errors and the exact
Rademacher bootstrap enumerating all $2^{18}$ sign patterns [@mackinnon2023].

**Placebos.** The realised forecast error in wind (registered) and the next day's forecast
penetration (exploratory) are each added to (1). Neither is known when day $d$'s auction
clears. A coefficient distinguishable from zero would signal a problem with timing or
measurement.

The hypotheses, specification and robustness set were registered before any panel
backtest ran (commit `6aa7cdc`). Five deviations were logged before the first regression,
two of them after the ceiling $V^*$ had been computed. Analyses added after the first
results, most at a referee's request, are labelled exploratory throughout. Appendix A
gives the full record, including two corrections to the deviation log.
