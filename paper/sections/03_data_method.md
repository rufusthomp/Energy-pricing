# Data

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

The sample comprises 19 zones chosen to span the range of European generation mixes:

| Type | Zones |
| --- | --- |
| Wind-heavy | DK_1, DK_2, DE_LU, NL, BE, PT, ES |
| Solar-growing | GR, IT_NORD |
| Nuclear-dominated | FR |
| Coal-heavy | PL, CZ |
| Hydro and nuclear | AT, CH, NO_2, SE_3, SE_4, FI, EE |

Great Britain is excluded because its ENTSO-E coverage ends in 2020–21. Ireland (SEM) is
excluded because its load forecast is almost entirely absent after mid-2021.

Two features of the data require care:

- **Resolution.** From October 2025 the day-ahead auction moved to a 15-minute market
  time unit in most zones. We average quarter-hours into hours, which is the price a
  battery holding a flat position over the hour receives.
- **The trading day.** Every coupled zone trades a *delivery day* defined on Central
  European Time, including zones whose civil time differs. In summer, Portugal and
  Ireland begin their trading day at 23:00 local time and Finland at 01:00. We verified
  this against the platform's own price documents. Every "day" in this paper is a CET
  delivery day: 24 hours, or 23 or 25 on clock-change days.

## Treatment variables

Our treatments are the TSOs' day-ahead forecasts, not realised generation. The day-ahead
price clears at 12:00 CET on D−1, before realised output is known, so forecasts are the
information on which the price is formed. For zone $z$ and delivery day $d$:

$$
\text{wind}_{zd} = 100 \times \frac{\sum_{h \in d} \widehat{W}_{zh}}{\sum_{h \in d} \widehat{L}_{zh}},
\qquad
\text{solar}_{zd} = 100 \times \frac{\sum_{h \in d} \widehat{S}_{zh}}{\sum_{h \in d} \widehat{L}_{zh}},
$$

where $\widehat{W}$, $\widehat{S}$ and $\widehat{L}$ are the forecast wind output, solar
output and load in MWh. A penetration is defined only when the forecasts cover every hour
of the day. Czechia publishes no wind forecast, so it drops out of the estimation sample,
which has 18 zones. It remains in the descriptive statistics.

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

The four operators differ **only** in the price vector they optimise against. Each
schedule is then settled at the day's actual prices.

| Operator | Optimises against | Information used |
| --- | --- | --- |
| Perfect foresight (PF) | Actual prices of day $d$ | The ceiling, $V^*_{zd}$ |
| Typical day (TD) | Mean price by market hour over days $d-28$ to $d-1$ | The recent calendar shape only |
| Persistence (PS) | Day $d-1$'s prices, by market hour | Yesterday only |

For TD, at least 20 of the 28 days must be complete. Every input is known by gate closure:
day $d-1$ cleared on $d-2$. Because every operator shares the same optimiser, the gap
between any two is a pure difference in information. The **capture share**
$100 \times V^{k}_{zd}/V^*_{zd}$ measures how much of the available value operator $k$
realises.

The TD operator is the conceptual centre. It knows everything about a day that its date
reveals: the season, the weekday pattern and the recent diurnal shape, including the
solar trough if the sun has been shining. It knows nothing specific to the day. Its
shortfall from the ceiling is therefore the part of arbitrage value that requires
day-specific information.

## Outcomes

- **Capture shares** of TD and PS. Days whose ceiling falls below the zone's 5th
  percentile are excluded, because a ratio with a near-zero denominator is meaningless.
- **Scale:** $\log V^*$.
- **Mechanism.**
  - *Shape novelty*: $1 - \operatorname{corr}(\boldsymbol{\pi}_d, \bar{\boldsymbol{\pi}}^{TD}_d)$,
    the extent to which the day's price shape departs from the typical day's.
  - The *daily spread*, $\max_h \pi_h - \min_h \pi_h$.

# Empirical strategy

We estimate

$$
Y_{zd} = \beta_w\, \text{wind}_{zd} + \beta_s\, \text{solar}_{zd}
+ \alpha_{z,y(d)} + \gamma_{z,m(d)} + \lambda_d + \varepsilon_{zd}.
\tag{1}
$$

The three sets of fixed effects each remove a named threat:

- **Zone-by-year effects** $\alpha_{z,y}$ absorb capacity build-out, market reforms and
  any zone-specific trend. Installed capacity is endogenous, and a penetration that trends
  alongside everything else in the sample is exactly the variation that produced spurious
  associations in earlier single-market specifications of this question (Appendix A).
- **Zone-by-month effects** $\gamma_{z,m}$ absorb each zone's seasonal cycle, including
  the solar season and the hydrological year.
- **Date effects** $\lambda_d$ absorb everything common to Europe on a given day: gas and
  carbon prices, the 2021–23 energy crisis, and the continental component of weather.

The remaining variation in $\text{wind}_{zd}$ and $\text{solar}_{zd}$ is day-to-day weather
within a zone-year-month, relative to other zones on the same day. Weather is not chosen
by any market participant, so we interpret $\beta$ as the causal effect of a day's
forecast renewable output on the outcome.

The **key hypothesis** (H1) is $\beta_w < \beta_s$ for TD capture: wind lowers the share
of value capturable from the calendar more than solar does. To test it as a single
coefficient, we re-parameterise (1) with $\text{wind}_{zd}$ and total variable
renewable penetration $\text{vre}_{zd} = \text{wind}_{zd} + \text{solar}_{zd}$ as
regressors. The coefficient on $\text{wind}$ is then exactly $\beta_w - \beta_s$.

**Inference.** Errors are clustered by zone. With 18 clusters, conventional
cluster-robust inference over-rejects [@cameron2008; @mackinnonwebb2018]. We therefore report
wild cluster restricted bootstrap p-values with Webb six-point weights [@webb2023] and
9,999 replications, computed on the fixed-effect-demeaned data.

**Placebo.** Adding the forecast error in wind (realised minus forecast, relative to
forecast load) should leave every day-ahead outcome unchanged, because the auction clears
before the error is realised. A non-zero coefficient would indicate a timing error in the
data, or a forecast series that embeds information unavailable at gate closure.

All hypotheses, specifications and robustness checks were registered before any panel
outcome was computed (commit `6aa7cdc`). Deviations are reported in Appendix A.
