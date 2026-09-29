# Results

Registered results are reported first in each subsection, and exploratory analyses are
labelled as such. Unless stated otherwise, effects are per 10 percentage points of
forecast penetration, and p-values come from the wild cluster restricted bootstrap.

## How much value there is, and who captures it

Table 1 summarises the panel. A 1 MW, 2-hour battery with perfect foresight of day-ahead
prices would have earned €153 per day on average across the 19 zones, or about €56,000
per MW per year from day-ahead arbitrage alone. This is a ceiling, not a forecast of
revenue. The ceiling varies more than threefold across zones. It is lowest in Norway's
reservoir-hydro zone NO_2 (€68), where hydro already smooths prices, and highest in
Estonia (€240) and Greece (€208).

$V^* = 0$ on 1,204 zone-days in 14 zones, 609 of them in NO_2. Prices are not flat on
these days. No intraday spread covered the battery's 15% round-trip loss. A capture
share is undefined on such days, and they are excluded from the share outcomes along with
days below each zone's 5th percentile of positive $V^*$.

{{table:t01_descriptives|Descriptive statistics by bidding zone, sorted by mean forecast wind penetration.}}

The typical-day operator, which knows the recent calendar shape and nothing about the
day, captures a mean of 73.4% of the ceiling on days where a share is defined. Weighted
by value, it captures 81.0%. Mean shares are pulled down by low-value days on which small
scheduling errors are large relative to the ceiling. NO_2 is the extreme case: its mean
share is 17.5% against a median of 67.6%. Persistence captures 64.0%. An operator that
trusts yesterday's prices does worse than one that averages the last four weeks, because
a single day's idiosyncrasies are more often noise than signal. The forecaster captures
76.3% (83.0% value-weighted). On the days both operate, it earns €3.45 per MW per day
more than the calendar operator, or 2.85 points of capture.

This is how much *this model* gains from the TSOs' fundamentals, not what the
information is worth. The forecaster is trained on squared price error, which need not
translate into arbitrage revenue. Its gain is largest in Spain (+7.4 points),
Italy North (+6.4) and Germany-Luxembourg (+6.0). In Finland, both Swedish zones and
Estonia it does no better than the calendar (Figure 1).

![Share of the perfect-foresight value captured by each operator, by zone. Zones are
ordered by mean forecast wind penetration, shown in brackets.](figures/f2_operators.pdf){width=95%}

## Which renewable creates arbitrage value

Table 2 reports the registered specification for every registered outcome.

{{table:t02_main|The effect of forecast wind and solar penetration on storage outcomes (registered).}}

The registered scale outcome is $\log V^*$ (H3, registered without a predicted
direction). Within a zone's year and season, and relative to other zones on the same day:

- **Solar creates arbitrage value.** 10 pp more forecast solar raises the day's
  perfect-foresight value by 28% (log $V^*$ +0.249, p < 0.001) and widens the daily
  spread by €22/MWh (p < 0.001).
- **Wind does not.** Its effect on value is small and insignificant (log $V^*$ −0.020,
  p = 0.26), and it *narrows* the spread by €3/MWh (p < 0.001). The registered hypothesis
  text predicted that wind would "raise [value], or reshape it". The first half of that
  prediction failed.

The registered outcome drops the 1,008 zone-days in the estimation sample with
$V^* = 0$. Keeping them changes nothing: $\log(1+V^*)$ gives +0.245 for solar, and in
euros solar adds €47.7 per MW per day (Table 11, exploratory). Figure 2 shows the
relationship is close to linear across the range of residual penetration.

![Binned scatter of log arbitrage value against residual forecast wind (left) and solar
(right) penetration. Both variables are residualised on the other treatment and on
zone×year, zone×month and date fixed effects, so the slope equals the regression
coefficient in Table 2. Each point is a vigintile of the residualised
treatment.](figures/f5_binscatter_value.pdf){width=100%}

Figure 3 shows two days in Germany-Luxembourg in 2024, chosen mechanically before any
regression as the days with the highest forecast wind and the highest forecast solar
penetration. Neither day has an unusual *shape*. Each correlates closely with the typical
day, with shape novelty of 0.086 and 0.088 against a zone-year mean
of 0.193. What differs is the amplitude. On the windiest day prices sat low and
flat, and the ceiling was €33 against a 2024 mean of €208. On the
sunniest day prices fell to −€60/MWh in the early afternoon, at the hours the typical day
predicted, and the ceiling was €364. The figure illustrates the scale effect,
not the shape effect. We return to shape next.

![Two days in DE_LU, 2024: day-ahead prices (solid) against the typical-day profile of
the previous 28 days (dashed). Left: the day with the highest forecast wind penetration.
Right: the day with the highest forecast solar penetration.](figures/f0_example_days.pdf){width=100%}

## The mechanism: how typical the day's shape is

Shape novelty, $1 - \operatorname{corr}(\boldsymbol{\pi}_d, \bar{\boldsymbol{\pi}}^{TD}_d)$,
measures how far a day's price shape departs from the typical day. The registered
hypothesis H2 predicted that wind raises it, and raises it more than solar does. Both parts
hold (Table 2, column 5; Figure 4):

- **Wind makes the day less typical:** +0.013 per 10 pp, p < 0.001.
- **Solar makes it more typical:** −0.051 per 10 pp, p = 0.001.

Wind varies far more from day to day than solar. After the fixed effects, the residual
standard deviation of wind penetration is 11.8 pp, against 2.9 pp for solar. Per standard
deviation, the two effects are of similar size and opposite sign (+0.016 and −0.015, each
about 7% of the mean novelty of 0.22). This comparison is exploratory.

![Binned scatter of shape novelty, 1 − corr(day's prices, typical-day profile), against
residual forecast wind (left) and solar (right) penetration. Construction as in Figure
2.](figures/f3_binscatter_novelty.pdf){width=100%}

A Pearson correlation with a fixed profile rises mechanically when the common diurnal
component grows relative to noise. So part of "solar makes the shape more typical" could
be "solar makes the shape bigger". Table 3 (exploratory) separates timing from amplitude:

- **A rank correlation**, which ignores amplitude, gives the same solar coefficient
  (−0.051) and a slightly smaller wind coefficient (+0.010).
- **Timing:** solar moves the day's price peak 0.53 hours and its trough 0.93 hours
  closer to the typical day's. Wind moves the peak 0.21 hours further away and has no
  effect on the trough.
- **Neighbours:** with region×date effects, which compare each zone only with its own
  coupling region, the solar coefficient falls to −0.037 and the wind coefficient to
  +0.012. Both remain significant.

{{table:t03_mechanism|Shape: amplitude, rank and timing.}}

Solar therefore makes the day more calendar-like in timing, not just in amplitude. Two
qualifications apply to the wind half, both from Section 6. The registered forecast-error
placebo fails for novelty. And the next day's forecast wind predicts today's novelty
about as strongly as today's does. Holding it fixed cuts the wind coefficient from 0.013
to 0.005 and leaves the solar coefficient unchanged. Solar's effect is a property of the
day. Wind's effect on shape belongs largely to multi-day weather regimes.

## Capture: the pre-registered test

Our key hypothesis (H1) was that wind lowers the share of value capturable from the
calendar more than solar does, so $\beta_w < \beta_s$ for typical-day capture. **The
test is inconclusive.** The difference has the predicted sign, −4.36 points of capture per
10 pp (standard error 2.59), with a WCB p-value of 0.120. The jackknife (CV3) p-value is
0.147. The exact Rademacher bootstrap, enumerating all $2^{18}$ sign patterns, gives
0.116.

The difference also decomposes against the hypothesis as registered, which said that
wind lowers calendar capture. Wind does not move it (−0.21, p = 0.74). The whole
difference comes from solar *raising* it (+4.15, p = 0.19). The same pattern, with more
precision, holds for the other operators: −6.42 (p = 0.042) for persistence and −4.67
(p = 0.071) for the forecaster.

![Binned scatter of typical-day capture share against residual forecast wind (left) and
solar (right) penetration. Construction as in Figure 2.](figures/f1_binscatter_td.pdf){width=100%}

The registered share outcome is badly conditioned, which we should have anticipated. A
capture share divides by $V^*$, and the zone-relative floor admits days on which $V^*$ is
a few euros. In NO_2 the floor is €0.82 per day, and its capture shares range down to
−6,613%. That one zone supplies most of the outcome's variance, and through the date
effects it adds noise to the solar coefficient even though NO_2 has no solar. Dropping
NO_2 moves the estimate to −6.45 (s.e. 1.44). We do not promote that or any other
variant to the headline, since choosing among constructions after seeing results is
exactly what registration exists to prevent. Section 6 reports them all.

Table 4 shows how the estimate moves as fixed effects are added (exploratory in
presentation). With zone and zone×month effects only, the difference is −9.65 and
conventionally significant at 1%. Adding zone×year effects leaves it at −8.75. Adding
date effects halves it. Common shocks across Europe account for much of the unconditional
association, which is why a single-market time series cannot answer this question. We
have not tested which common shocks those are.

{{table:t04_fe_buildup|How the estimate moves as fixed effects are added.}}

## The value that requires information

The capture share combines two things: the ceiling, and what the operator misses. Table
5 (exploratory) separates them in euros.

{{table:t05_information|The value that requires information, in euros (exploratory).}}

- **The calendar operator's shortfall does not respond to either technology.** It leaves
  €30.8 per MW per day on the table on average. A windier day changes that by −€0.50
  (p = 0.38), and a sunnier one by −€1.55 (p = 0.24). The two do not differ (p = 0.46).
- **Solar raises the calendar operator's revenue one-for-one with the ceiling.** Its
  revenue rises by €49.3 per 10 pp of solar (p < 0.001, Table 11), against €47.7
  for the ceiling.
- **The forecaster's advantage falls on windy days.** Its gain over the calendar falls by
  0.78 points of capture per 10 pp of wind (p = 0.003), or €0.63 per day (p = 0.057).
  Solar does not move it.

These results change the reading of H1. A share rises whenever the ceiling rises and the
absolute shortfall does not, and that is what happens with solar. So the H1 difference
is mostly a restatement of the scale result: solar adds value the calendar can find, and
wind adds none. Neither technology creates value that only a forecaster can reach. The
wind result is the opposite of what our motivation predicted. At the day-ahead stage the
TSO wind forecast helps this forecaster *less* on windy days. One interpretation is that
windy days are when the day-ahead price already reflects the wind forecast most fully,
leaving less for a model to add. We have not tested it.

## Heterogeneity: wind's cost rests on one zone

The registered heterogeneity test (H4) interacts forecast wind penetration with $K$, the
zone-year's mean wind penetration. The interaction is −0.35 points of typical-day capture
per 10 pp of wind, per additional 10 pp of $K$ (s.e. 0.08, WCB p = 0.027). H4 is
confirmed as registered. Table 6 shows that it rests on a single zone.

{{table:t06_heterogeneity|Heterogeneity in the wind effect by the system's wind share.}}

Denmark West (DK_1) is the only zone with $K$ above 38%. Its zone-years run from 51% to
66%. It also carries a third of the identifying variation in wind (Table 10). At DK_1's
mean $K$ of 58%, the registered model implies that a windier day lowers calendar capture
by 0.94 points per 10 pp (s.e. 0.34). At the estimation-sample mean ($K$ = 18.4%) the
effect is +0.46 (s.e. 0.49). Without DK_1 the interaction is −0.41 with a standard error
of 0.40 (p = 0.63). Without both Danish zones it changes sign. Splitting zone-years into terciles of $K$ gives wind slopes of −1.47, +0.70 and −0.40 from the lowest tercile to the highest, with no monotone pattern (highest minus lowest +1.07, p = 0.81). The
forecaster's advantage over the calendar does not grow with $K$ either
(the interaction is +0.08 points, p = 0.35, or −€0.13 per day, p = 0.11).

So the registered result is a statement about one system, not a pattern across systems.
$K$ is also not randomly assigned. High-wind systems differ in interconnection, hydro
access and market design, any of which could modulate how wind weather reaches prices.
