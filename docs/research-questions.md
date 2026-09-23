# Candidate research questions from the panel data

Brainstormed 2026-09-23, before any panel result has been seen. The purpose is to choose
one primary question deliberately rather than keep whichever of many happens to produce a
significant coefficient. With a dozen outcomes and several specifications each, something
will clear p < 0.05 by chance, and this project has already retracted two claims.
**Choose from this list, then record the choice in `research-design.md` before running
anything.**

## Citation discipline

Every reference below was recalled from memory, not retrieved. Each carries a confidence
mark: **[H]** means confident that the paper exists as described; **[M]** means confident it
exists, less sure of the exact title, year or venue. None should be cited in a draft until
it has been found and read. Where no reference is given, none was recalled with enough
confidence to name.

## What the data supports

21 bidding zones, hourly, 2019 to 2026: day-ahead price, actual load, generation by type,
TSO day-ahead forecasts of load, wind and solar, and annual installed capacity. On top of
that sits the MILP ceiling, a naive rule, persistence and a gradient-boosted forecaster.

The data has one property that most of the literature lacks: **the TSO day-ahead forecast
is observed alongside the realised outcome.** Day-ahead prices clear on expectations, so
the forecast is the right regressor for a day-ahead price, and the forecast error should
not move that price at all. That yields a built-in placebo test, and several of the ideas
below depend on it.

---

## 1. The value of information in storage arbitrage as renewables rise
*The current primary. Full design in `research-design.md`.*

**Question.** Holding weather fixed, does more installed wind and solar capacity mean a
larger share of storage value is captured only by forecasting?

**Literature.** Storage arbitrage valuation: Sioshansi, Denholm, Jenkin and Weiss (2009,
*Energy Economics*) on PJM **[H]**, which also compares perfect foresight against simple
backcast rules; and Walawalkar, Apt and Mancini (2007, *Energy Policy*) on New York
**[M]**. Price forecasting: Weron (2014, *International Journal of Forecasting*) **[H]**
and Lago, Marcjasz, De Schutter and Weron (2021, *Applied Energy*), with an open benchmark
**[H]**.

**Gap.** As far as recalled, the foresight gap is measured as a level in one market. It has
not been measured as something that *changes with the generation mix*, identified from
weather variation across many markets. That is the contribution, if the literature search
confirms nobody has done it.

**Feasibility.** High. The infrastructure exists. The risk is that β₂ comes out as zero,
which is a publishable result anyway.

## 2. The shape effect: renewables and the intraday spread, not the price level

**Question.** A large literature estimates how wind and solar lower the *level* of the
price (the merit-order effect). Storage earns from the *shape*: the daily spread, the
evening ramp, the midday trough. How does forecast renewable output move the shape, and
how does that differ between wind and solar?

**Literature.** The merit-order effect: Sensfuß, Ragwitz and Genoese (2008, *Energy
Policy*) **[H]**; Cludius, Hermann, Matthes and Graichen (2014, *Energy Economics*)
**[M]**. Volatility: Ketterer (2014, *Energy Economics*) on German wind **[M]**.

**Contribution.** A multi-zone estimate of the effect on *shape*, using the forecast as the
regressor, with the forecast error as the placebo. If realised-minus-forecast output moves
the day-ahead price, something is wrong with either the data or the timing.

**Feasibility.** Very high, and cheap: no battery model is needed. It is also the **first
stage** of idea 1. Idea 1's mechanism is weather → shape → capture, and this establishes
the first arrow. The strongest paper probably contains both.

## 3. The value of storage as renewables grow, and when incumbents saturate it

**Question.** Hirth showed that the market value of wind and solar falls as their share
rises (cannibalisation). The mirror question: does the value of *flexibility* rise with
renewable share, and does incumbent storage (pumped hydro) compress it?

**Literature.** Hirth (2013, *Energy Economics*) on value factors **[H]**. López Prol,
Steininger and Zilberman (2020, *Energy Economics*) on cannibalisation in California
**[M]**. For hydro acting as a battery for neighbouring wind: Green and Vasilakos (2012,
*Energy Journal*) on Denmark and Norway **[M]**, and Mauritzen (2013, *Energy Journal*) on
Nordic hydro and wind **[M]**. On equilibrium effects of storage entry: Butters, Dorsey and
Gowrisankaran, NBER working paper on battery investment in California **[M]**, and
Karaduman's job-market paper on grid storage in South Australia **[M]**.

**Contribution.** A "storage value factor" measured across 21 zones. The short-run part
(weather) is well identified. The long-run part (capacity) is cross-sectional and weaker,
and should be presented as such.

**Feasibility.** High for the ceiling `V*`, which is idea 1's scale effect. The
incumbent-storage part is descriptive unless interconnection is added (see idea 8).

## 4. The Iberian exception as a shock to price formation

**Question.** From June 2022, Spain and Portugal capped the gas price used in power
bidding. What did that do to the daily spread, and therefore to the value of storage? The
policy debate was about the price *level*. The effect on flexibility is a separate and
less-studied question.

**Design.** Difference-in-differences, and the only genuine one available here. ES and PT
are treated, the other zones are controls, and the policy has real start and end dates.
Event-study leads test pre-trends.

**The catch, to deal with before anything else.** France imported cheap capped Iberian
power over the interconnector, so France was partly treated. That breaks the assumption
that the control group is untouched by the treatment. France has to be dropped from the
control group or modelled as spillover. The same may apply more weakly to its neighbours.

**Literature.** There is policy and academic work on the Iberian exception, including by
Natalia Fabra, who helped design it. No specific paper can be named with confidence. This
is the first thing to search.

**Feasibility.** High, and fast. It is **the best candidate for a short, clean standalone
paper**, and could be written while idea 1's forecasting sweep runs.

## 5. Negative prices: frequency, drivers and support-scheme design

**Question.** Negative prices are becoming common in high-renewable zones, and they are
where storage earns most per hour. Some of the negativity is caused by support-scheme
design: generators paid per MWh keep producing below zero. Do zones whose schemes stop
paying during negative-price hours see fewer of them?

**Literature.** Nicolosi (2010, *Energy Policy*) on German negative prices **[M]**; Fanone,
Gamba and Prokopczuk (2013, *Energy Economics*) **[M]**.

**Feasibility.** Medium. The data is easy, but support-scheme rules must be coded by
country and date by hand, and those rules changed several times. Germany's rule on support
during negative-price periods has been tightened repeatedly, which could give
within-country variation. That history needs checking from primary sources.

## 6. Forecast quality as a public good

**Question.** TSO forecast accuracy varies across zones and has improved over time. Does
better public forecast quality raise the capture of *unsophisticated* operators, narrowing
the premium? If it does, public forecasting is a policy lever over who captures storage
value. That connects directly to the market-structure motivation of idea 1.

**Data.** Forecast error is directly observable: forecast minus actual, for wind, solar and
load, by zone and day. This needs no new data.

**Feasibility.** Medium. The endogeneity worry is that zones with harder-to-forecast
weather have both worse forecasts and different price shapes. Zone-by-month effects handle
much of that. This works well as a **section of idea 1** rather than a paper of its own.

## 7. The 2021–23 energy crisis: a windfall of scale or of shape?

**Question.** Storage revenue soared during the gas crisis. How much of that was scale
(everything more expensive, so spreads proportionally wider) and how much was shape (a
different intraday pattern)? The answer bears on whether storage business cases built on
crisis-era revenues can persist.

**Feasibility.** High, but mostly **descriptive**, because date effects absorb the crisis
in the main design. Suits a motivating section or figure rather than a paper.

## 8. Transmission and storage as substitutes (needs more data)

**Question.** Interconnection lets a zone import flexibility instead of storing it. As zones
are coupled, do local spreads compress and the value of local storage fall?

**Literature.** Mauritzen (2013) and Green and Vasilakos (2012) above are the empirical
anchors. Most of the rest is system modelling rather than econometrics.

**Feasibility.** Low to medium. It needs cross-border flows and capacities, which the pull
does not fetch. ENTSO-E has them (`query_crossborder_flows`), but the data is per border
pair, which multiplies requests. It is ambitious and economically important, and it also
supplies the control that idea 1's remaining threat asks for.

## 9. The 15-minute market time unit (watch, don't pursue yet)

The single day-ahead coupling moved to 15-minute products in October 2025. That could
change intraday shape and short-duration storage value. But every coupled zone switched on
the same day, so there is no control group. GB is outside the coupling, but its ENTSO-E
coverage ends in 2020 to 2021. There is also only about a year of post-period. Revisit in
2027.

---

## Recommendation

**One paper, three parts:**

1. **Idea 2 (shape) is the first stage**: renewables, via exogenous forecast weather,
   reshape the intraday price, with the forecast error as the placebo.
2. **Idea 1 (information) is the headline**: whether that reshaping moves value from
   rule-following operators to forecasting ones. It reports the scale effect (idea 3's
   ceiling) and the information effect side by side.
3. **Idea 6 (forecast quality) is the policy extension**: whether public forecasts close the
   gap.

That is a coherent causal chain, weather → shape → who captures value → what policy can do
about it, and each link has its own literature to engage.

**Separately, idea 4 (Iberian exception) as a short second paper.** It is clean, fast and
built on the same data, and it does not depend on the forecasting sweep. It is also the
lowest-risk path to a finished piece.

**Not recommended as primaries:** 5 (too much hand-coding of policy for the payoff), 7
(descriptive), 8 (data-heavy; better as a later extension), 9 (no control group yet).

## Before writing a word of the paper

1. Search Google Scholar and the recalled papers' reference lists for idea 1's specific
   claim: *foresight gap varying with renewable penetration.* If it has been done, the
   contribution shifts to the multi-zone weather identification. If that has also been
   done, idea 2 or idea 4 becomes the primary.
2. The same for idea 4: what has been published on the Iberian exception since 2023, and
   does any of it look at spreads rather than levels?
3. Record the chosen primary, and its single primary outcome, in `research-design.md`.
