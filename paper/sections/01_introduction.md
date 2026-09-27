# Introduction

Grid-scale batteries are being built across Europe on the expectation that the price
volatility created by wind and solar will pay for them. That expectation has two parts
that are usually run together. The first is that renewables create arbitrage value:
they depress prices when they produce and leave scarcity when they do not, widening the
intraday spreads a battery trades on. The second, rarely stated, is that the value can be
captured by whoever owns the battery. This paper is about the second part. Arbitrage
value exists only in hindsight. An operator commits its schedule in the day-ahead auction
before prices are known. What it earns depends on how much of the day's price shape it
can anticipate.

The information needed to anticipate that shape depends, we argue, on *which* renewable
creates it. Solar output follows the sun. On a clear day it carves a trough into the
middle of the day at the same clock hours as on every other clear day, so the value it
creates recurs at predictable times: a schedule learned from recent weeks will largely
find it. Wind output follows weather systems that arrive and depart at no particular
hour, so the value it creates sits wherever the weather puts it, and capturing it
requires knowing the day. If this is right, the two technologies of decarbonisation
differ in more than their levelised cost and value factor. Solar creates storage value
that is *public*, available to any operator who knows the calendar. Wind creates storage
value that is *informational*, available only to operators who forecast.

That distinction matters beyond the private economics of batteries. If the value of
storage increasingly depends on forecasting capability, the returns to operating
storage accrue to firms with scale in data, modelling and trading. That has implications
for the market structure of flexibility, and for the public value of the forecasts that
transmission system operators already publish. It also implies that a system
decarbonising mainly through wind and one decarbonising mainly through solar will
reward different kinds of storage operator.

We test the argument on hourly day-ahead prices for 19 European bidding zones from 2019
to 2026, a panel spanning Danish and German wind, Iberian and Greek solar, French nuclear
and Polish coal. We model a price-taking 1 MW, 2-hour battery operated four ways, which
differ only in the information used to set the schedule:

1. **Perfect foresight**, which defines the ceiling.
2. **Typical day**, which optimises against the mean price profile of the previous four
   weeks, and so knows the calendar and nothing about the day.
3. **Persistence**, which optimises against yesterday's prices.
4. **Forecaster**, which adds a gradient-boosted correction built from the TSOs' day-ahead
   wind, solar and load forecasts.

The share of the ceiling each operator captures measures how much of the day's value its
information set reaches. Our treatments are the TSOs' own day-ahead forecasts of wind and
solar output, which are the information on which the auction clears. Identification
comes from weather. With zone-by-year, zone-by-month and date fixed effects, the
remaining variation in forecast penetration is day-to-day weather within a zone's year
and season, relative to other zones on the same day. This design is a response to the
central difficulty of the question. Renewable penetration trends upward everywhere,
alongside everything else that changed over the decade, and a specification that lets
that trend through will find an association between any two series that happen to rise
together.

RESULTS_PARAGRAPH

The paper makes three contributions:

1. **Existing work computes the perfect-foresight value of storage arbitrage across
   European zones** [@mercier2023], or measures forecast-based capture within one or two
   markets [@hornek2025; @falezza2026]. We combine an operator ladder with cross-market
   variation to ask where the value of information *comes from*.
2. **We show that the renewable technology matters**, extending to storage the literature
   showing that wind and solar affect price formation asymmetrically [@hirth2013;
   @lopezprol2020].
3. **We provide a design for identifying renewable effects from weather** that is robust
   to the common trends that have undermined time-series evidence on this question. All
   hypotheses and specifications were registered before any outcome was computed.

Section 2 reviews related work. Section 3 describes the data and the operators, and
Section 4 the empirical strategy. Section 5 presents results, Section 6 robustness and
limitations, and Section 7 concludes.
