# Introduction

Grid-scale batteries are being built across Europe on the expectation that the price
volatility created by wind and solar will pay for them. That expectation has two parts
that are usually run together. The first is that renewables create arbitrage value:
they depress prices when they produce and leave scarcity when they do not, widening the
intraday spreads a battery trades on. The second, rarely stated, is that the value can be
captured by whoever owns the battery. Arbitrage value exists only in hindsight. An
operator commits its schedule in the day-ahead auction before prices are known, and what
it earns depends on how much of the day's price shape it can anticipate.

This paper asks both questions of the same data, and asks them separately for wind and
solar. We had a hypothesis about the second. Solar output follows the sun, so the value
it creates should recur at the same clock hours and be found by a schedule learned from
recent weeks. Wind output follows weather systems that arrive at no particular hour, so
the value it creates should sit wherever the weather puts it and reward operators who
forecast the day. If so, a system decarbonising through wind would reward a different
kind of storage operator from one decarbonising through solar.

We test this on hourly day-ahead prices for European bidding zones from 2019 to 2026.
The panel spans Danish and German wind, Iberian and Greek solar, French nuclear, Nordic
hydro and Polish coal. We model a price-taking 1 MW, 2-hour battery operated four ways,
which differ only in the information used to set the schedule:

1. **Perfect foresight**, which defines the ceiling.
2. **Typical day**, which optimises against the mean price profile of the previous four
   weeks, and so knows the calendar and nothing about the day.
3. **Persistence**, which optimises against yesterday's prices.
4. **Forecaster**, which adds a gradient-boosted correction built from the TSOs' day-ahead
   wind, solar and load forecasts.

Our treatments are the TSOs' day-ahead forecasts of wind and solar output as a share of
forecast load. Zone-by-year, zone-by-month-of-year and date fixed effects remove capacity
build-out, each zone's seasonal cycle and every shock common to Europe on a day. What
remains is mostly day-to-day weather. It is not weather alone, and Section 6 sets out
what else it contains. The design responds to the central difficulty of the question:
renewable penetration trends upward everywhere, alongside everything else that changed
over the decade, and a specification that lets that trend through will find an
association between any two rising series. The hypotheses, specification and robustness
set were registered before any backtest ran. A referee's report on the first draft found
an error in our bootstrap and several overstatements; the corrected results are reported
here, and every analysis added after the first results is labelled exploratory.

The main findings are these.

- **Solar creates arbitrage value; wind does not** (registered outcome, no registered
  direction). A day with 10 percentage points more forecast solar offers 28% more
  perfect-foresight value, about €48 per MW per day, and a €22/MWh wider spread. A windier
  day offers no more value and a slightly narrower spread. The solar result survives every
  identification check we or the referee devised, but it shrinks by about 40% when zones
  are compared only with their own neighbours.
- **Solar makes the day's price shape more typical, and wind makes it less typical**
  (registered, H2). Solar also moves the day's peak and trough towards the hours the
  calendar predicts. The wind effect is smaller than it first appears: about 60% of it is
  explained by the next day's wind, and its placebo test fails.
- **The value that requires information does not change with the renewable mix**
  (exploratory). The calendar operator leaves about €31 per MW per day on the table, and
  neither wind nor solar moves that shortfall. Solar raises the calendar operator's revenue
  one-for-one with the ceiling. The forecaster's advantage over the calendar does not rise
  on windy days; it falls.
- **Our pre-registered test is inconclusive** (H1). The calendar operator's *share* of the
  ceiling rises more with solar than with wind, by 4.4 points per 10 pp, with a
  wild-bootstrap p-value of 0.12. Given the third finding, the share difference is mostly
  a restatement of the first: solar adds value the calendar can find, and wind adds none.
- **A registered heterogeneity result rests on one zone** (H4). Wind lowers calendar
  capture more in wind-heavy systems, but only because of Denmark West. Without it the
  interaction is imprecise and of either sign.

So the renewable mix changes how much storage value there is. We find no evidence that it
changes who can capture it. For the day-ahead market, the premise that wind-driven
systems reward forecasting sophistication is not supported by these data, and the
premise that solar creates capturable value is.

The paper makes three contributions:

1. **It separates the size of storage value from its accessibility.** Existing work
   computes the perfect-foresight value of arbitrage across European zones
   [@mercier2023], or measures forecast-based capture within one or two markets
   [@hornek2025; @falezza2026]. Combining an operator ladder with cross-market variation
   lets us ask how each part responds to the generation mix.
2. **It extends to storage the evidence that wind and solar shape prices asymmetrically**
   [@hirth2013; @lopezprol2020; @bushnell2021], with identification from forecast
   penetration under date fixed effects across 18 zones.
3. **It reports a pre-registered test honestly, including the parts that failed.** The
   registration, deviation log, referee report and corrections are part of the public
   record, and the paper is compiled from the code that produces every number in it.

Section 2 reviews related work. Section 3 describes the data and the operators, and
Section 4 the empirical strategy. Section 5 presents results, Section 6 robustness and
limitations, and Section 7 concludes.
