# Related literature

This paper connects three literatures that have developed largely separately: the
valuation of storage arbitrage, the effect of variable renewables on wholesale price
formation, and electricity price forecasting.

**Storage arbitrage valuation.** The standard approach values a price-taking store by
optimising its dispatch against historical prices under perfect foresight.
@sioshansi2009 apply it to PJM and also estimate the welfare effects of storage at scale;
@walawalkar2007 value energy arbitrage and regulation services in New York; and
@sioshansi2010 examine how ownership structure changes the welfare calculus. For Europe,
@zafeirakis2016 backtest arbitrage strategies across day-ahead markets. They find value
concentrated in less integrated, import-dependent and less competitive markets, which
attributes the cross-market dispersion to market structure. Closest to our setting,
@mercier2023 compute the perfect-foresight value of a price-taking battery for every
EU-28 bidding zone, plus Norway, Switzerland and Turkey, varying efficiency and duration.
Our ceiling $V^*$ is their object. We take it as the denominator and ask what share of it
operators with less information realise.

A smaller and more recent literature measures that share directly, within a single
market. @hornek2025 find that a forecast-driven battery captures around 89% of
perfect-foresight revenue in the German continuous intraday market. @falezza2026, trading
German and Swiss day-ahead, intraday and reserve markets, finds that capture depends on
the rank correlation between forecast and realised prices rather than on conventional
error metrics. Forecasts above a high rank-correlation threshold capture almost all of
the perfect-foresight revenue, while persistence captures about a third. This is the
single-market counterpart to our mechanism. Our shape-novelty variable measures,
day by day, how far the realised price shape departs from the shape a calendar-based
operator expects. What neither paper can do with one or two markets is ask how capture
varies with the generation mix, which is the variation our panel supplies.

**Renewables and price formation.** Variable renewables enter the merit order at near-zero
marginal cost and depress prices when they produce [@sensfuss2008]. Regression evidence
for Germany puts the effect at roughly €1 per MWh for each additional GWh of wind and
solar [@cludius2014]. @ketterer2014 shows that German wind lowers the price level but
raises its volatility, and volatility is the raw material of arbitrage. Because
renewables depress prices precisely when they produce, their own market value falls
with penetration [@hirth2013]. In California, wind and solar cannibalise each other
asymmetrically: wind penetration lowers solar's value factor while solar penetration
raises wind's [@lopezprol2020]. That asymmetry between the two technologies in price
formation is the price-side analogue of the asymmetry we test on the storage side. The
merit-order literature is concerned mainly with the *level* of prices. Our outcome
depends on their *intraday shape*, and specifically on whether that shape is predictable
from the calendar.

**Renewables and the value of flexibility.** If renewables raise volatility, they should
raise the value of storage, and equilibrium studies confirm that storage investment
responds to renewable-driven volatility. @butters2025 model battery entry in California,
finding it economic without subsidy only at high renewable shares, with the first
tranches of storage doing most to reduce prices. @karaduman2023 finds a non-monotonic
relationship in South Australia: storage first erodes renewable revenues by flattening
prices, then raises them once renewable capacity is large enough to face curtailment.
Hydro reservoirs have long performed this role. Danish exports track Nordic reservoir
levels rather than wind directly [@greenvasilakos2012], and wind shifts the shadow value
of stored water in Norwegian hydro areas [@mauritzen2013]. These studies establish that
renewables change *how much* flexibility is worth. Our question is *who can capture it*:
whether the value renewables create is available to any operator who knows the season,
or only to one who knows the day.

**Price forecasting.** Electricity price forecasting is a mature field [@weron2014].
Recent work stresses rigorous, comparable benchmarking [@lago2021], and shows that
European forecasts improve when neighbouring coupled markets are included
[@lago2018]. That last finding matters for identification here. Under market coupling, a
zone's price responds to its neighbours' weather, so our wind coefficient measures the
effect of wind weather in a zone's region rather than of strictly domestic output. We
return to this in Section 6. We use forecasting instrumentally. Our forecaster exists to
measure how much of the value lost by a calendar-based operator is recoverable with
information available at gate closure, not to compete on forecast accuracy.

**Inference.** Our design has a moderate number of natural clusters: 18 bidding zones in
the estimation sample. Cluster-robust inference is unreliable at this size
[@cameron2008], and the wild cluster bootstrap with six-point weights gives more reliable
p-values [@webb2023]. We follow that recommendation. Our treatments are continuous, not
staggered binary adoptions, so the negative-weighting problems of two-way fixed effects
under staggered timing [@dechaisemartin2020; @goodmanbacon2021] do not arise in their
canonical form. Heterogeneity in effects across zones remains a concern, which we address
with leave-one-zone-out estimates.

**Data.** The ENTSO-E Transparency Platform is the only harmonised public source for this
panel, and it has documented quality problems: inconsistent labelling, gaps and
revisions [@hirth2018]. We report our coverage audit and exclusions in full in Section 3.
