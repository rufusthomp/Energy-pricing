# Annotated bibliography — "Sun is a clock, wind is a lottery"

All entries below were verified in this session via WebSearch/WebFetch (search results, publisher
pages, or the Crossref API) against the exact authors, year, title and venue reported. The
verification source (DOI or URL) is given for each. Anything I could not pin down to that standard
is listed under "Unverified leads" rather than presented as a citation.

---

## Gap assessment

No paper I could find runs the specific comparative test this paper proposes: whether the gap
between perfect-foresight and realistic-operator storage arbitrage value widens with **wind**
penetration but not with **solar** penetration, across multiple markets, with weather-instrumented
identification. Several works sit close to it from different angles, and it is worth being precise
about how each differs.

**Closest in setting**: Mercier, Olivier & De Jaeger (2023, *Energy Economics*) compute the
perfect-foresight MILP arbitrage value of a price-taking battery in every EU-28 bidding zone plus
Norway, Switzerland and Turkey, hourly, across many years — the same geography, frequency and
method as this paper's foresight ceiling. But it stops at the ceiling: it does not add a
persistence, typical-day or ML operator, does not compute a *capture share*, and does not
decompose results by renewable technology mix. It is the natural predecessor this paper extends.

**Closest in mechanism**: two very recent working papers quantify the foresight-vs-forecast gap
directly. Hornek et al. (2025, arXiv:2501.07121) find a forecast-driven battery captures ~89% of
perfect-foresight value in the German continuous intraday market. Falezza (2026, arXiv:2604.12082)
shows, across German/Swiss multi-market battery dispatch, that a forecast's *rank correlation*
with true prices (not its MAE) is what predicts the capture ratio — a methodological cousin of this
paper's information-value framing. Neither, however, brings renewable composition into the
comparison; both treat the renewable mix as a background feature of one or two markets rather than
a treatment varied across many.

**Closest on the renewables side**: Lopez Prol, Steininger & Zilberman (2020) and Hirth (2013) show
wind and solar erode their *own* market value differently as penetration rises (cannibalization,
value factors) — the price-formation half of this paper's mechanism — but neither connects this to
what an operator needs to *know* to capture storage value. Zafeirakis et al. (2016) cross-market-compare
arbitrage value across Europe with market-structure covariates (import dependence, market power)
but not a renewable-mix decomposition or an operator ladder.

**Verdict**: the gap is real. The pieces — perfect-foresight ceilings across the same 19+ zones,
forecast-vs-foresight capture ratios in one or two markets, and wind/solar cannibalization
econometrics — exist separately in the literature, but no paper combines them into a cross-market,
multi-operator, wind-vs-solar identification of *where the value of information in storage
arbitrage comes from*. That combination is this paper's contribution.

---

## 1. Energy storage arbitrage valuation

**Sioshansi, R., Denholm, P., Jenkin, T., & Weiss, J. (2009). "Estimating the value of electricity
storage in PJM: Arbitrage and some welfare effects." *Energy Economics*, 31(2), 269–277.**
DOI: [10.1016/j.eneco.2008.10.005](https://doi.org/10.1016/j.eneco.2008.10.005)
Computes the arbitrage value of a price-taking storage device in PJM (2002–2007) under perfect
foresight of day-ahead prices, and the welfare effects of large-scale storage on the market.
Direct anchor for this paper's foresight-ceiling construction; PJM/US analogue this paper extends
to 19 European zones and adds imperfect-information operators.

**Walawalkar, R., Apt, J., & Mancini, R. (2007). "Economics of electric energy storage for energy
arbitrage and regulation in New York." *Energy Policy*, 35(4), 2558–2568.**
DOI: [10.1016/j.enpol.2006.09.005](https://doi.org/10.1016/j.enpol.2006.09.005)
Values NaS batteries and flywheels for arbitrage plus regulation in NYISO, sensitivity-testing
round-trip efficiency and revenue stacking. Establishes the "arbitrage vs regulation revenue"
framing later work (including this paper, which isolates pure arbitrage) had to disentangle.

**Sioshansi, R. (2010). "Welfare Impacts of Electricity Storage and the Implications of Ownership
Structure." *The Energy Journal*, 31(2), 173–198.**
DOI: [10.5547/ISSN0195-6574-EJ-Vol31-No2-7](https://doi.org/10.5547/ISSN0195-6574-EJ-Vol31-No2-7)
Extends the PJM arbitrage analysis to ask how welfare effects differ when storage is owned by a
merchant, a load-serving entity, or a system operator. Relevant background on why this paper treats
the battery as a price-taking merchant arbitrageur rather than a welfare-maximizing planner.

**Mercier, T., Olivier, M., & De Jaeger, E. (2023). "The value of electricity storage arbitrage on
day-ahead markets across Europe." *Energy Economics*, 123, 106721.**
DOI: [10.1016/j.eneco.2023.106721](https://doi.org/10.1016/j.eneco.2023.106721)
Builds a MILP perfect-foresight price-taker storage model and runs it on every EU-28 bidding zone
plus Norway, Switzerland and Turkey, hourly, across multiple years, varying round-trip efficiency
(50–100%) and duration (1–10h). This is the closest existing paper in geography, frequency and
method to this paper's foresight ceiling; it does not add imperfect-information operators or a
renewable-mix decomposition, which is exactly the gap this paper fills (see Gap assessment).

**Zafeirakis, D., Chalvatzis, K. J., Baiocchi, G., & Daskalakis, G. (2016). "The value of arbitrage
for energy storage: Evidence from European electricity markets." *Applied Energy*, 184, 971–986.**
DOI: [10.1016/j.apenergy.2016.05.047](https://doi.org/10.1016/j.apenergy.2016.05.047)
Backtests pumped-hydro and compressed-air arbitrage strategies across European day-ahead markets,
finding arbitrage value concentrated in less-integrated, import-dependent, less competitive
markets. Supports this paper's motivation for cross-market comparison but attributes value
dispersion to market structure rather than renewable composition or information availability.

**Hornek, T., Lee, Y., Potenciano Menci, S., & Pavić, I. (2025). "The Value of Battery Energy
Storage in the Continuous Intraday Market: Forecast vs. Perfect Foresight Strategies." arXiv:2501.07121.**
URL: [arxiv.org/abs/2501.07121](https://arxiv.org/abs/2501.07121) (preprint, not yet verified as
peer-reviewed)
Using 2023 German continuous intraday data, a forecast-driven 1 MW/1 MWh battery captures roughly
89% of perfect-foresight annual revenue. Direct methodological precedent for this paper's "capture
share" outcome variable, in a single market with no renewable-mix decomposition.

**Falezza, A. (2026). "When Forecast Accuracy Fails: Rank Correlation and Decision Quality in
Multi-Market Battery Storage Optimization." arXiv:2604.12082.**
URL: [arxiv.org/abs/2604.12082](https://arxiv.org/abs/2604.12082) (preprint, not yet verified as
peer-reviewed)
Trading day-ahead, continuous intraday and reserve markets in Germany/Switzerland (2020–2025),
finds forecasts above a Kendall-tau rank-correlation threshold of ~0.85–0.95 capture 97–100% of
perfect-foresight revenue, while persistence forecasts (tau near zero) capture only ~33%. Directly
relevant methodological finding: forecast *quality metric choice* matters for measuring the value
of information, and the persistence-operator capture number (~33%) is a useful benchmark for this
paper's own persistence operator.

---

## 2. Renewables and wholesale price formation

**Sensfuß, F., Ragwitz, M., & Genoese, M. (2008). "The merit-order effect: A detailed analysis of
the price effect of renewable electricity generation on spot market prices in Germany." *Energy
Policy*, 36(8), 3086–3094.**
DOI: [10.1016/j.enpol.2008.03.035](https://doi.org/10.1016/j.enpol.2008.03.035)
Introduces the "synthetic supply curve" simulation approach to estimate how privileged renewable
feed-in shifts the merit order and depresses spot prices in Germany, finding the price-suppression
effect in 2006 exceeded that year's net renewable support payments. Foundational method for the
price-formation mechanism this paper's treatment (wind/solar penetration) operates through.

**Cludius, J., Hermann, H., Matthes, F. C., & Graichen, V. (2014). "The merit order effect of wind
and photovoltaic electricity generation in Germany 2008–2016: Estimation and distributional
implications." *Energy Economics*, 44, 302–313.**
DOI: [10.1016/j.eneco.2014.04.020](https://doi.org/10.1016/j.eneco.2014.04.020)
Regression-based estimate that a 1 GWh rise in German/Austrian wind+solar output lowers day-ahead
prices by roughly €1.1–1.3/MWh, cumulating to €6/MWh (2010) and €10/MWh (2012) average price
suppression. Empirical regression benchmark for the magnitude of renewables' price effect that this
paper's zone-by-year/month fixed effects specification must be consistent with.

**Ketterer, J. C. (2014). "The impact of wind power generation on the electricity price in
Germany." *Energy Economics*, 44, 270–280.**
DOI: [10.1016/j.eneco.2014.04.003](https://doi.org/10.1016/j.eneco.2014.04.003)
GARCH model showing German wind generation lowers the price level but raises its daily volatility;
the merit-order effect and the volatility effect both attenuate over time as market/regulatory
design adapts. Directly supports this paper's premise that wind raises price volatility (the raw
material for arbitrage) without making it more forecastable day-ahead.

**Hirth, L. (2013). "The market value of variable renewables: The effect of solar wind power
variability on their relative price." *Energy Economics*, 38, 218–236.**
DOI: [10.1016/j.eneco.2013.02.004](https://doi.org/10.1016/j.eneco.2013.02.004)
Shows the market value (revenue per MWh relative to the average price) of wind and solar falls as
their penetration rises, because their own output is correlated with when prices are already
depressed by their generation. Core reference for the "value factor" concept and for why this
paper's treatment must be identified off exogenous weather variation rather than realized output.

**Lopez Prol, J., Steininger, K. W., & Zilberman, D. (2020). "The cannibalization effect of wind
and solar in the California wholesale electricity market." *Energy Economics*, 85, 104552.**
DOI: [10.1016/j.eneco.2019.104552](https://doi.org/10.1016/j.eneco.2019.104552)
Time-series analysis of CAISO (2013–2017) showing solar and wind each erode their own value factor
as penetration rises, and that wind penetration reduces solar's value factor while solar penetration
*raises* wind's — an asymmetric cross-cannibalization result. Directly relevant contrast/support:
this paper's hypothesis that wind and solar interact asymmetrically with storage value echoes this
asymmetric cross-technology finding in price formation.

---

## 3. Renewables, storage/flexibility value, and hydro as incumbent storage

**Butters, R. A., Dorsey, J., & Gowrisankaran, G. (2025). "Soaking Up the Sun: Battery Investment,
Renewable Energy, and Market Equilibrium." *Econometrica*, 93(3), 891–927.** (Working paper
version: NBER Working Paper No. 29133, 2021.)
DOI: [10.3982/ECTA20411](https://doi.org/10.3982/ECTA20411)
Structural equilibrium model of battery entry in California, showing storage investment responds
to renewable-driven price volatility but remains negligible without subsidy until renewable shares
are high; first tranches of storage most reduce wholesale prices. Equilibrium counterpart to this
paper's partial-equilibrium, price-taking setting — relevant for interpreting whether the
information-value mechanism this paper documents would survive storage entry at scale.

**Karaduman, Ö. (2023). "Economics of Grid-Scale Energy Storage in Wholesale Electricity Markets."
Stanford Graduate School of Business Working Paper No. 4126.** (Earlier version: MIT CEEPR Working
Paper 2021-005.)
URL: [gsb-faculty.stanford.edu/omer-karaduman/files/2022/09/Economics-of-Grid-Scale-Energy-Storage.pdf](https://gsb-faculty.stanford.edu/omer-karaduman/files/2022/09/Economics-of-Grid-Scale-Energy-Storage.pdf)
Dynamic equilibrium model of grid-scale storage in the South Australian market, finding a
non-monotonic relationship: storage initially reduces renewable generators' revenue by flattening
prices, but once VRE capacity roughly doubles, storage instead *raises* renewable returns by
preventing curtailment. Relevant for this paper's discussion of how the storage-renewables
relationship could shift as wind/solar penetration keeps rising — I was not able to verify this
paper has since appeared in a peer-reviewed journal, so it is cited as a working paper.

**Green, R., & Vasilakos, N. (2012). "Storing Wind for a Rainy Day: What Kind of Electricity Does
Denmark Export?" *The Energy Journal*, 33(3), 1–22.**
DOI: [10.5547/01956574.33.3.1](https://doi.org/10.5547/01956574.33.3.1)
Shows Danish cross-border trade tracks thermal output and Nordic hydro reservoir levels, not wind
generation directly, and estimates wind output volatility costs Denmark 4–8% of its market value.
Empirical demonstration of hydro-as-storage substituting for domestic flexibility — the paper's
closest real-world analogue to what a "perfect information" battery operator would do with wind's
volatility, absent forecasting skill.

**Mauritzen, J. (2013). "Dead Battery? Wind Power, the Spot Market, and Hydropower Interaction in
the Nordic Electricity Market." *The Energy Journal*, 34(1), 103–124.**
DOI: [10.5547/01956574.34.1.5](https://doi.org/10.5547/01956574.34.1.5)
Distributed-lag models show wind power shifts the shadow value of stored water in Norwegian hydro
areas, i.e., hydro flexibility absorbs wind's volatility at the system level. Directly relevant
prior showing wind's system-level effect operates through storage/flexibility shadow prices, which
is the mechanism this paper's battery is a stylized instrument for measuring.

---

## 4. Electricity price forecasting

**Weron, R. (2014). "Electricity price forecasting: A review of the state-of-the-art with a look
into the future." *International Journal of Forecasting*, 30(4), 1030–1081.**
DOI: [10.1016/j.ijforecast.2014.08.008](https://doi.org/10.1016/j.ijforecast.2014.08.008)
Comprehensive review of day-ahead electricity price forecasting methods (statistical, computational
intelligence, hybrid) and evaluation practice. Standard reference for framing this paper's
persistence, typical-day and ML forecaster operators against the field's benchmark taxonomy.

**Lago, J., Marcjasz, G., De Schutter, B., & Weron, R. (2021). "Forecasting day-ahead electricity
prices: A review of state-of-the-art algorithms, best practices and an open-access benchmark."
*Applied Energy*, 293, 116983.**
DOI: [10.1016/j.apenergy.2021.116983](https://doi.org/10.1016/j.apenergy.2021.116983)
Reviews forecasting methods, critiques inconsistent benchmarking practice in the literature, and
releases an open-access forecasting toolbox (epftoolbox) with standardized backtests. Direct
methodological reference for this paper's ML price-forecaster operator and its evaluation protocol.

**Lago, J., De Ridder, F., Vrancx, P., & De Schutter, B. (2018). "Forecasting day-ahead electricity
prices in Europe: The importance of considering market integration." *Applied Energy*, 211,
890–903.**
DOI: [10.1016/j.apenergy.2017.11.098](https://doi.org/10.1016/j.apenergy.2017.11.098)
Shows day-ahead price forecasts for one European market improve when neighbouring, interconnected
markets' prices are included as predictors, i.e., market coupling matters for forecastability.
Relevant caveat for this paper's 19-zone panel: cross-zone price coupling under SDAC may confound
a purely domestic wind/solar forecastability story unless coupling is controlled for.

---

## 5. Econometrics: weather as exogenous variation, few-cluster inference, TWFE caveats

**Cameron, A. C., Gelbach, J. B., & Miller, D. L. (2008). "Bootstrap-Based Improvements for
Inference with Clustered Errors." *The Review of Economics and Statistics*, 90(3), 414–427.**
DOI: [10.1162/rest.90.3.414](https://doi.org/10.1162/rest.90.3.414)
Shows standard cluster-robust asymptotics over-reject with few (5–30) clusters and proposes a wild
cluster bootstrap-t that restores correct size. Directly applicable to this paper's inference: with
19 bidding zones as the natural clustering unit, few-cluster corrections are needed for the
treatment coefficients on wind/solar penetration.

**MacKinnon, J. G., & Webb, M. D. (2018). "The wild bootstrap for few (treated) clusters." *The
Econometrics Journal*, 21(2), 114–135.**
DOI: [10.1111/ectj.12107](https://doi.org/10.1111/ectj.12107)
Shows the ordinary wild cluster bootstrap can fail when the *treated* cluster count is small
(distinct from the total cluster count), and proposes a subcluster wild bootstrap fix, noting the
fix requires similar cluster sizes regardless of treatment status. Relevant caveat if this paper's
identification exploits a small number of zone-years with unusual wind/solar shocks.

**Webb, M. D. (2023). "Reworking wild bootstrap-based inference for clustered errors." *Canadian
Journal of Economics/Revue canadienne d'économique*, 56(3), 839–858.**
DOI: [10.1111/caje.12661](https://doi.org/10.1111/caje.12661)
Proposes a six-point bootstrap weight distribution (and a kernel density alternative) that gives
more reliable p-values than the standard two-point Rademacher weights when the number of clusters
is small (below ~12). Directly applicable inference recommendation given this paper's 19-zone
cluster count sits in the range where six-point weights outperform Rademacher weights.

**de Chaisemartin, C., & D'Haultfœuille, X. (2020). "Two-Way Fixed Effects Estimators with
Heterogeneous Treatment Effects." *American Economic Review*, 110(9), 2964–2996.**
DOI: [10.1257/aer.20181169](https://doi.org/10.1257/aer.20181169)
Shows TWFE regression coefficients are a weighted average of underlying treatment effects with
possibly negative weights, so a TWFE coefficient can have the wrong sign even when all true effects
are positive. Relevant caveat only if this paper's zone-by-year/month fixed-effects design is
reinterpreted as a staggered-adoption/event-study design rather than a continuous-treatment panel;
flagged per the brief's "only if relevant" instruction.

**Goodman-Bacon, A. (2021). "Difference-in-differences with variation in treatment timing."
*Journal of Econometrics*, 225(2), 254–277.**
DOI: [10.1016/j.jeconom.2021.03.014](https://doi.org/10.1016/j.jeconom.2021.03.014)
Decomposes the TWFE DiD estimator into a variance-weighted average of all possible 2x2
comparisons, showing already-treated units used as controls bias the estimate under dynamic
effects. Same caveat-scope as de Chaisemartin & D'Haultfœuille above: relevant only insofar as
wind/solar penetration is treated as a staggered binary/ordinal treatment rather than continuous.

---

## 6. European market design and data context

**Hirth, L., Mühlenpfordt, J., & Bulkeley, M. (2018). "The ENTSO-E Transparency Platform – A review
of Europe's most ambitious electricity data platform." *Applied Energy*, 225, 1054–1067.**
DOI: [10.1016/j.apenergy.2018.04.048](https://doi.org/10.1016/j.apenergy.2018.04.048)
Reviews the ENTSO-E Transparency Platform's scope and diagnoses data-quality shortcomings
(inconsistent labelling, gaps, revisions) to governance failures: data providers face no incentive
to fix errors and ACER's oversight is non-binding. Essential methods reference for this paper's raw
data source; any wind/solar forecast series construction should account for the documented quality
issues.

**ENTSO-E. "Single Day-Ahead Coupling (SDAC)."**
URL: [entsoe.eu/network_codes/cacm/implementation/sdac](https://www.entsoe.eu/network_codes/cacm/implementation/sdac/)
Official description of the pan-European day-ahead price-coupling mechanism (EUPHEMIA algorithm)
under the CACM regulation. Institutional source (not peer-reviewed) establishing why this paper's
19 bidding zones share a common price-formation mechanism rather than being fully independent
markets.

**European Commission (2025). "EU electricity trading in the day-ahead markets becomes more
dynamic."**
URL: [energy.ec.europa.eu/news/eu-electricity-trading-day-ahead-markets-becomes-more-dynamic-2025-10-01_en](https://energy.ec.europa.eu/news/eu-electricity-trading-day-ahead-markets-becomes-more-dynamic-2025-10-01_en)
Official notice of the 30 September 2025 EU-wide transition from hourly to 15-minute day-ahead
market time units (MTU). Institutional source establishing a structural break this paper's
2019–2026 sample must accommodate (e.g., via date or zone-by-period fixed effects, or by working
with hourly aggregates post-transition).

---

## Unverified leads

- **"The Impact of Energy Arbitrage on the Market Value of Solar Power Across Europe"** —
  found via ResearchGate (record id 405438723), evaluates utility-scale PV market value and BESS
  arbitrage profitability across 29 European countries using 2024 data (PV market value range
  35–90 €/MWh; BESS arbitrage profitable in only ~40% of countries studied). I could not confirm
  the author names, exact venue (journal vs. preprint), or a DOI despite repeated searches, so it
  is not cited as a reference. If it turns out to be a refereed 2025/2026 paper, it would belong in
  strand 2 (value factors) and strand 1 (arbitrage capture) and is worth chasing down directly via
  the ResearchGate page or Google Scholar rather than search snippets.

- **A cross-country empirical paper testing wind-vs-solar forecastability as a driver of storage
  capture ratios** (the exact gap identified above) — I searched extensively (Google Scholar-style
  queries, arXiv, SSRN framing, Energy Economics/Applied Energy/Energy Journal-targeted queries)
  and did not find one. This absence is itself the answer to the gap-check question, not a search
  failure to caveat away — see the Gap assessment above for the closest substitutes and exactly how
  they differ.

- **Karaduman (2023) journal status** — cited above as a working paper (Stanford GSB WP No. 4126);
  I could not confirm whether it has since been accepted at a journal. Worth re-checking before
  submission.

- **Hornek et al. (2025, arXiv:2501.07121) and Falezza (2026, arXiv:2604.12082) peer-review status**
  — both cited above as preprints; I could not confirm journal publication for either. Both are
  recent (2025–2026) and may still be under review.

---

## Referee-suggested additions (verified 2026-09-27)

All seven references below were verified against Crossref (`https://api.crossref.org/works/<DOI>`),
cross-checked with a direct Crossref lookup by DOI, for exact title, authors, journal, volume,
pages and DOI. BibTeX keys added to `references.bib`: `bushnell2021`, `cullen2013`, `novan2015`,
`rintamaki2017`, `wozabal2016`, `mackinnonwebb2017`, `mackinnon2023`.

**Bushnell, J., & Novan, K. (2021). "Setting with the Sun: The Impacts of Renewable Energy on
Conventional Generation." *Journal of the Association of Environmental and Resource Economists*,
8(4), 759–796.** DOI: [10.1086/713249](https://doi.org/10.1086/713249). Verified via Crossref and
the published abstract (NBER WP 24980 is the working-paper precursor). Studies California's
wholesale market response to utility-scale solar expansion; see finding D below.

**Cullen, J. A. (2013). "Measuring the Environmental Benefits of Wind-Generated Electricity."
*American Economic Journal: Economic Policy*, 5(4), 107–133.** DOI:
[10.1257/pol.5.4.107](https://doi.org/10.1257/pol.5.4.107). Verified via Crossref. Estimates the
emissions wind power offsets in the Texas (ERCOT) grid by identifying which conventional plants it
displaces; finds the offset value exceeds renewable subsidy cost only under high estimates of the
social cost of pollution.

**Novan, K. (2015). "Valuing the Wind: Renewable Energy Policies and Air Pollution Avoided."
*American Economic Journal: Economic Policy*, 7(3), 291–326.** DOI:
[10.1257/pol.20130268](https://doi.org/10.1257/pol.20130268). Verified via Crossref. Shows the
marginal external (air-pollution) benefit of wind generation varies by location and time of day,
because it depends on which conventional generator is on the margin when wind displaces it.

**Rintamäki, T., Siddiqui, A. S., & Salo, A. (2017). "Does renewable energy generation decrease the
volatility of electricity prices? An analysis of Denmark and Germany." *Energy Economics*, 62,
270–282.** DOI: [10.1016/j.eneco.2016.12.019](https://doi.org/10.1016/j.eneco.2016.12.019). Verified
via Crossref. Directly relevant to this paper's wind-vs-solar and daily-vs-weekly volatility
questions; see finding C below.

**Wozabal, D., Graf, C., & Hirschmann, D. (2016). "The effect of intermittent renewables on the
electricity price variance." *OR Spectrum*, 38(3), 687–709.** DOI:
[10.1007/s00291-015-0395-x](https://doi.org/10.1007/s00291-015-0395-x). Verified via Crossref
(published online 7 March 2015; print issue 2016, matching the referee's cited year). Finds small-
to-moderate quantities of intermittent renewables tend to decrease day-ahead price variance, while
large quantities increase it — a non-monotonic penetration effect relevant to this paper's framing
of wind/solar as raising the volatility "raw material" for storage arbitrage.

**MacKinnon, J. G., & Webb, M. D. (2017). "Wild Bootstrap Inference for Wildly Different Cluster
Sizes." *Journal of Applied Econometrics*, 32(2), 233–254.** DOI:
[10.1002/jae.2508](https://doi.org/10.1002/jae.2508). Verified via Crossref. Distinct from the
already-cited MacKinnon & Webb (2018) "wild bootstrap for few (treated) clusters": this earlier
paper shows the conventional wild cluster bootstrap can under- or over-reject when cluster sizes are
very unequal (not just few), and proposes a variant robust to that imbalance. Relevant if this
paper's 19 bidding zones have very unequal numbers of zone-year observations.

**MacKinnon, J. G., Nielsen, M. Ø., & Webb, M. D. (2023). "Cluster-robust inference: A guide to
empirical practice." *Journal of Econometrics*, 232(2), 272–299.** DOI:
[10.1016/j.jeconom.2022.04.001](https://doi.org/10.1016/j.jeconom.2022.04.001). Verified via
Crossref. A synthesis/practitioner's guide to modern cluster-robust inference (bootstrap and
non-bootstrap methods, choice of clustering variable, few-cluster diagnostics); a natural single
citation for this paper's inference-methodology paragraph alongside the more specific MacKinnon–Webb
papers.

### A. Sioshansi, Denholm, Jenkin & Weiss (2009) — backcasting rule and share of perfect-foresight value

**Not independently verified to the standard this brief requires.** I confirmed the paper's
bibliographic details and abstract via Crossref (DOI 10.1016/j.eneco.2008.10.005) and via the
publisher/ADS record, but could not obtain the paper's full text in this session: ScienceDirect
returned 403 (paywalled), the OSTI.gov PDF mirror (`osti.gov/servlets/purl/1353367`,
`osti.gov/biblio/1353367`) and NREL's `docs.nrel.gov` were both unreachable from this environment
(connection refused / DNS failure), and a PDF pulled from the author's CMU page turned out to be a
different, password-protected file. Multiple web-search summarizer passes returned mutually
inconsistent numbers for the "share of perfect-foresight value captured" (variously ~85%, ~89%,
84–90%, 91–95%, and an 8-hour/20-hour storage-duration framing) — the inconsistency across repeated
searches is itself evidence these are unreliable paraphrases rather than a grounded quote, so I am
not reporting any of them as verified. **No quote is provided because I could not access the
abstract or text to a standard I trust.** What I can confirm from the verified abstract: the paper
computes price-taking storage arbitrage value in PJM (2002–2007) under perfect foresight of
day-ahead prices and analyses welfare effects of larger-scale storage; the abstract itself does not
mention a "backcasting" rule, so if one exists it is in the paper's body/results section, which I
could not read. **Recommendation:** access the paper directly (e.g. via institutional
ScienceDirect access) before citing a specific capture percentage in the working paper; do not use
any of the numbers surfaced above without checking them against the PDF directly.

### B. Ketterer (2014) — daily or intraday volatility?

**Daily (day-to-day), not intraday.** Crossref/publisher abstract (DOI 10.1016/j.eneco.2014.04.003):
"This paper investigates the relationship between intermittent wind power generation and electricity
price behaviour in Germany. Using a GARCH model, I evaluate the effect of wind electricity
generation on the level and the volatility of the electricity price in an integrated approach. The
results show that variable wind power reduces the price level but increases its volatility."
Independently, two RePEc/EconPapers-indexed descriptions of the paper (for the published version and
its ifo Working Paper No. 143 precursor) state it "introduces daily levels of German wind power
generation as [an] explanatory variable in the mean and the variance equation of a GARCH model of
the German day-ahead electricity price" — i.e. the GARCH model is fit on a daily (day-ahead) price
series with daily wind-generation as the regressor, so the "volatility" it estimates is day-to-day
volatility of the day-ahead price, not within-day (intraday/hourly) volatility. I could not open the
ifo working-paper PDF itself as readable text to pull a page-level quote confirming this from the
methods section directly, so this answer rests on the abstract plus the RePEc description rather
than a body-text quote.

### C. Rintamäki, Siddiqui & Salo (2017) — wind vs solar, daily vs weekly volatility

Per the publisher abstract/summary (DOI 10.1016/j.eneco.2016.12.019, Crossref-verified): wind power
**decreases** the volatility of **daily** prices in Denmark (attributed to a flattening of the
intraday price profile) but **increases** daily-price volatility in Germany (attributed to a
relatively stronger impact on off-peak prices); solar power decreases price volatility in Germany.
However, **weekly** volatility of prices increases in both Denmark and Germany, which the paper
attributes to renewables' intermittency. In short: the wind effect on daily volatility has opposite
signs in the two countries, while both wind and solar leave weekly volatility higher in both
countries.

### D. Bushnell & Novan (2021) — solar and the intraday price profile

Per the publisher abstract/summary (DOI 10.1086/713249, Crossref-verified): solar expansion in
California reduced the **daily average** wholesale price, but that average masks a reshaping of the
**intraday profile** — a substantial **decrease in midday prices** (when solar output peaks) **combined
with an increase in shoulder-hour prices** (morning and evening, when solar output is low). I could
not pull a page-level verbatim quote from the paper's own text (only the publisher/working-paper
abstract and search summaries were accessible in this session), so this is reported at
abstract-level confidence, not a direct textual quote.
