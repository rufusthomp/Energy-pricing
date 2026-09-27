# Results

## How much value there is, and who captures it

Table 1 summarises the panel. A 1 MW, 2-hour battery with perfect foresight of
day-ahead prices would have earned €153 per day on average across the 19 zones, or about
€56,000 per MW per year from day-ahead arbitrage alone. This is a ceiling, not a
forecast of revenue. The ceiling varies more than threefold across zones:

- **Lowest:** Norway's reservoir-hydro zone NO_2 (€68), where hydro already smooths
  prices and 22% of days have perfectly flat prices and zero value.
- **Highest:** Estonia (€240) and Greece (€208).

{{table:t1_descriptives|Descriptive statistics by bidding zone, sorted by mean forecast wind penetration.}}

Figure 1 illustrates the mechanism the paper tests. It shows two days in
Germany-Luxembourg in 2024, selected mechanically as the days with the highest forecast
wind and the highest forecast solar penetration. On the windiest day (24 November, wind
forecast at 93% of load), prices sat near zero for the whole day. The typical evening
peak simply did not happen, and there was almost nothing to arbitrage. On the sunniest
day (11 August, solar at 37% of load), prices fell to −€60/MWh in the early afternoon.
That trough came at the hours the typical day predicted, only much deeper. The value
was large, and a schedule learned from the calendar would have found it.

![Two days in DE_LU, 2024: day-ahead prices (solid) against the typical-day profile of
the previous 28 days (dashed). Left: the day with the highest forecast wind penetration.
Right: the day with the highest forecast solar penetration.](figures/f0_example_days.pdf){width=100%}

The typical-day operator, which knows the recent calendar shape and nothing about the
day, captures on average 73.4% of the ceiling on the days where a capture share is
defined. Persistence captures 64.0%. An operator that trusts yesterday's prices does
worse than one that averages the last four weeks, because a single day's idiosyncrasies
are more often noise than signal. The forecaster, which adds a correction built from the
TSOs' day-ahead fundamentals, captures 76.0%. Day-specific information is therefore
worth 2.6 points of capture on average over the calendar alone.

That gain is unevenly distributed (Figure 2). It is largest in Germany-Luxembourg
(+5.8 points), Spain (+7.1) and Italy North (+6.5). In all four Nordic and Baltic zones
(Finland, both Swedish zones and Estonia) the forecaster does slightly worse than the
calendar, by 0.4 to 1.2 points. Norway is an outlier on every measure, for the reason above.

![Share of the perfect-foresight value captured by each operator, by zone. Zones are
ordered by mean forecast wind penetration, shown in brackets.](figures/f2_operators.pdf){width=95%}

## Which renewable creates arbitrage value

Table 2 reports the pre-registered specification for every outcome. Each column
regresses the outcome on forecast wind and solar penetration, per 10 percentage points
of forecast load, with zone×year, zone×month and date fixed effects.

{{table:t2_main|The effect of forecast wind and solar penetration on storage outcomes.}}

The clearest result concerns the scale of the opportunity (columns 4 and 6, Figure 3).
Within a zone's year and season, and relative to other zones on the same day:

- **Solar creates arbitrage value.** 10 pp more forecast solar raises the day's
  perfect-foresight value by 28% (log V* +0.249, WCB p = 0.001) and widens the daily
  spread by €22/MWh (p < 0.001).
- **Wind does not.** Its effect on value is small and insignificant (−2.0% per 10 pp,
  p = 0.25), and it *narrows* the spread by €3/MWh (p = 0.003).

The two technologies differ in how much they vary from day to day. After the fixed
effects, the residual standard deviation of wind penetration is 11.8 pp, against 2.9 pp
for solar. Scaled to one standard deviation, a sunny day raises arbitrage value by 7.4%
and a windy day lowers it by 2.4%.

The mechanism is visible in Figure 1. A windy day lowers the whole price curve through
the merit order more than it reshapes it. A sunny day deepens the midday trough against
an evening peak that solar cannot reach.

![Binned scatter of log arbitrage value against residual forecast wind (left) and solar
(right) penetration. Both variables are residualised on the other treatment and on
zone×year, zone×month and date fixed effects, so the slope equals the regression
coefficient in Table 2. Each point is a vigintile of the residualised
treatment.](figures/f5_binscatter_value.pdf){width=100%}

## The mechanism: how typical the day's shape is

The hypothesis concerns not how much value there is but where in the day it sits. Shape
novelty measures directly how far a day's price shape departs from the typical day. It
moves exactly as hypothesised (Table 2, column 5; Figure 4):

- **Wind makes the day less typical:** +0.013 per 10 pp, WCB p < 0.001.
- **Solar makes it more typical:** −0.051 per 10 pp, p = 0.001.
- **The difference** is 0.064 (p < 0.001).

Per standard deviation of weather the two effects are equal and opposite, at +0.016 and
−0.015, each about 7% of the mean novelty of 0.22. Sunny days reinforce the shape the
calendar predicts; windy days depart from it. This is the "sun is a clock" half of the
hypothesis, measured on prices rather than on revenue.

![Binned scatter of shape novelty, 1 − corr(day's prices, typical-day profile), against
residual forecast wind (left) and solar (right) penetration. Construction as in Figure
3.](figures/f3_binscatter_novelty.pdf){width=100%}

## Capture: the pre-registered test

Our key hypothesis (H1) was that wind lowers the share of value capturable from the
calendar more than solar does, so $\beta_w < \beta_s$ for typical-day capture. **The
estimate has the predicted sign but is only marginally significant.** The difference is
−4.36 points of capture per 10 pp (standard error 2.59, WCB p = 0.099, Table 2 column 1).

It also decomposes differently from the hypothesis as phrased. Wind barely moves
typical-day capture (−0.21, p = 0.72). The difference comes from solar *raising* it
(+4.15, p = 0.16). The same pattern holds for the other operators:

| Operator | β_w − β_s | WCB p |
| --- | --- | --- |
| Persistence | −6.42 | 0.029 |
| Forecaster | −4.69 | 0.068 |

Figure 5 shows the typical-day relationship.

We read this as consistent with the mechanism, though not conclusive about capture.
Solar makes arbitrage value larger and more calendar-shaped, and calendar-based
operators capture a larger share of it. Wind makes the day's shape less typical, but on
average across the panel, it does not measurably reduce what a calendar operator
captures. Section 5.5 shows that this average conceals heterogeneity by system. We did
not register a one-sided test, so we report the two-sided p-value as registered.

![Binned scatter of typical-day capture share against residual forecast wind (left) and
solar (right) penetration. Construction as in Figure 3.](figures/f1_binscatter_td.pdf){width=100%}

Table 3 shows why the date fixed effects are essential, and how an unconditional
analysis would have misled. With only zone and season effects, the solar coefficient is
roughly twice as large. The wind-minus-solar difference is then −8.75, and
conventionally "significant at 1%". Adding date effects halves both. Much of the naive
association comes from days that are sunny across Europe at once, and those coincide
with Europe-wide conditions, such as fuel prices and continental demand, that
independently shape spreads. A single-market time-series analysis cannot remove that
common component, which is why this question needs a panel.

{{table:t3_fe_buildup|How the estimate moves as fixed effects are added.}}

## Heterogeneity: wind's cost grows with wind's share

The pre-registered heterogeneity test (H4) interacts forecast wind penetration with the
zone-year's mean wind penetration $K$. The interaction is −0.35 points of typical-day
capture per 10 pp of wind, per additional 10 pp of $K$ (standard error 0.08, WCB
p = 0.02).

Evaluated at the panel mean ($K$ = 18.4%), a windy day has no significant effect on
calendar capture (+0.48, s.e. 0.50). In a low-wind system with $K$ = 5%, it slightly
raises it, by about +0.9 points per 10 pp. In a system with Denmark West's wind share
($K \approx$ 58%), it lowers it by about 0.9 points per 10 pp.

So the informational cost of wind is not a constant. It appears as wind comes to
dominate a system, which is the structural direction the introduction asked about. One
caution applies. $K$ is not randomly assigned, so this is heterogeneity in the effect of
weather, not the causal effect of building wind capacity. High-wind systems differ from
others in interconnection, hydro access and market design, and any of these could
modulate how wind weather reaches prices.
