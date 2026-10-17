# Response to the referee

**Manuscript:** "Is the Sun a Clock?", now retitled "More Value, Not More Information:
Wind, Solar and the Returns to Electricity Storage Arbitrage in Europe".

We thank the referee for an unusually thorough report. The replication found a real error
in our inference, and several of the concerns changed what the paper claims. The
revision accepts the report's central recommendation, which was to rebuild the paper
around what the data show.

Table numbers below refer to the revised paper. Every analysis added in response is
labelled exploratory there, and the pre-registration's correction log
(`docs/preregistration.md`) records each factual correction.

**Status key:**

- **Done:** the request was carried out as asked.
- **Partly:** a substitute that addresses the concern was carried out.
- **Not done:** the request was not carried out; the reason is given, and the point is
  stated as a limitation in the paper.

## Major concerns

### M1. Framing claims more than the registered test supports: Done

- **Title, abstract, introduction and conclusion** are rewritten. The "public" and
  "informational" value claims are deleted, and so is "the sun behaves like a clock".
- **Every result is labelled** by status:
  - H1 is inconclusive (p = 0.120).
  - H2 holds, with the placebo and lead caveats.
  - H3 has no registered direction.
  - H4 holds as registered but is driven by DK_1.
- **The claims the referee listed are corrected:**
  - "Precisely estimated" and "stable across every check" are gone.
  - "Robust to common trends" is gone.
  - "Treatments vary with weather alone" is replaced by an account of what else the
    variation contains (Section 6).
- **The failed half of the registered hypothesis** ("wind would raise value") is stated
  as failed in Section 5 and in Appendix A.

### M2. The forecaster contradicts the value-of-information thesis: Done

- **Done.** Table 5 adds the euro shortfalls V\* − TD and V\* − FC, and FC − TD in € and
  in pp, as outcomes. The referee's result replicates: FC − TD falls with wind (−0.78 pp,
  p = 0.003). It is now reported as a finding, and it motivates the new title.
- **Done.** The H4 analogue on FC − TD is in Table 7. The interaction is +0.08 pp
  (p = 0.35) and −€0.13 (p = 0.11). The forecaster's advantage does not grow with a
  system's wind share.
- **Done.** "Exactly the value of information" is withdrawn everywhere: the paper,
  deviation 3 (via a correction) and the code docstring. The 2.6-point difference of
  means over different samples is replaced by the same-sample gain: €3.45 per day, or
  2.85 points.
- **Done, in a limited form: a forecaster aimed at what arbitrage pays for.** A second
  forecaster is trained on the within-day price shape, with each day's mean removed from
  the target (Table 6). Daily rank correlations between every plan and realised prices are
  reported as outcomes, following Falezza (2026).
  - **The shape forecaster is better overall:** 77.3% capture against 76.5%, and €4.98
    against €3.44 per day over the calendar.
  - **Its advantage still does not rise with wind:** −0.22 pp per 10 pp (p = 0.029) and
    −€0.18 (p = 0.45).
  - **Wind lowers the calendar plan's rank correlation, but neither forecaster recovers
    it.**

  It is not decision-focused in the strict sense of training on revenue end to end, and
  Section 6 says so. Re-running the registered forecaster with the modified code
  reproduced every stored daily revenue exactly.

### M3. The capture share is ill-conditioned; in euros H1 is a scale effect: Done

- **(a)** The ill-conditioning is stated plainly in Section 5, including NO_2's €0.82
  floor, the −6,613% minimum and NO_2's contamination of the solar coefficient through
  the date effects. The statement that "Norway identifies only the wind coefficient" is
  deleted. We did not promote an alternative construction, for the reason the referee
  gives.
- **(b)** Alternative constructions are reported without selection in Section 6.
- **(c)** The euro decomposition is reported (Tables 5 and 13). The calendar operator's
  shortfall does not respond to either technology (difference p = 0.46), and its revenue
  rises with solar by about as much as the ceiling does. Section 5 now says the H1 share
  difference is "mostly a restatement of the scale result". We report the decomposition
  in euros, not as log V_TD, because TD revenue is zero or negative on 7% of zone-days.
  We did not register it as an amendment, since results had already been seen; it is
  exploratory.
- **(d)**
  - The zero-value facts are corrected: 1,204 days in 14 zones, and not flat.
  - The 1,008-day drop from log V\* is disclosed in Table 2.
  - log(1 + V\*) and V\* in € are reported in Table 13.

### M4. The wild cluster bootstrap is mis-implemented: Done

- **The fix.** The bootstrap re-projects each cluster's residual block off the fixed
  effects, as the referee proposed. It reproduces the referee's H1 p-value of 0.1197
  exactly. Every WCB p-value in the paper uses the corrected code.
- **Alternative inference.**
  - The CV3 jackknife gives p = 0.147.
  - The Rademacher WCB, fully enumerated over 2^18 patterns, gives p = 0.116.
  - Partial leverage by zone is in Table 12. DK_1 carries a third of the wind variation;
    Greece carries the largest share of the solar variation, at 15%.
- **Cross-cluster dependence.**
  - Two-way clustering is reported, and the paper notes that it *lowers* the standard
    error.
  - Driscoll–Kraay standard errors are much smaller still. The paper explains why we do
    not rely on them: they protect against serial dependence only within the lag window.
  - Region-level clustering with four regions is too few for any cluster-robust
    method, so we did not use it. Region×date fixed effects address the substance of the
    concern (M5b).

### M5. Identification threats

- **(a) Fixed-effect description: Done.** The text now describes the fixed effects as
  additive, and the zone×year×month specification is reported. It moves every solar
  coefficient away from zero.
- **(b) Market coupling: Done.**
  - Region×date effects are a main robustness check (Tables 3, 10 and 13). They cut solar's
    effect on log V\* by about 40%, and the paper says so in the abstract-level summary
    (Section 1).
  - Neighbours' mean forecast penetration is added as a control (Table 14). This is a
    regional mean, not interconnection-weighted, because we do not have interconnection
    capacities for the full panel.
  - The SUTVA violation is discussed explicitly (Section 6).
- **(c) The denominator: Done, as far as the public record allows.**
  - Done: the fixed-denominator treatment (Tables 10 and 13), a log load control (Table
    14), and the regression of forecast load on the treatments (Section 6).
  - Which TSOs publish load net of embedded generation:
    - **Documented for two zones:** Denmark (Energinet does not observe small rooftop
      systems) and Belgium (Elia estimates unmeasured decentralised generation and adds it).
    - **Partly documented for Germany:** the regulator's consumption series counts only
      electricity drawn from the grid.
    - **Not documented for the rest:** no public statement either way.

    Section 6 reports this, with sources, and the notes are in
    `docs/tso-forecast-practices.md`. The weather instruments do not depend on the load
    forecast at all.
- **(d) Forecast timing: Done, except where the data do not exist.**
  - Done: the text no longer claims the treatments are the auction's information set.
    The non sequitur about regressors is deleted, and the curtailment concern is stated.
    Excluding negative-price days is reported (Tables 10 and 13) and changes nothing.
  - **Weather instruments: done (Table 15).** Forecast penetration is instrumented with
    ERA5 reanalysis wind and solar at fixed points in each zone. Both first stages are
    strong. Weak-instrument-robust reduced-form tests support the scale, shape and
    value-of-information results. Realised weather cannot respond to prices, to the auction
    or to curtailment, so this addresses the timing and endogeneity concern directly.
  - **Publication timestamps cannot be recovered.** The platform's documentation and its
    raw responses show that it records no submission or revision time, only the time of
    the query. The series we use is the fixed 18:00 D−1 vintage. The load forecast is
    served at its latest revision. Section 6 states both.
- **(e) The placebo: Done.**
  - TOST equivalence tests are added (Table 8). They confirm the referee's point that the
    placebo "passes" only through imprecision.
  - PS capture is added.
  - The measurement-error reading is presented as one of two conjectures, alongside the
    referee's frontal-day alternative.
  - The attenuation claim is deleted.
  - The lead placebo is added. Tomorrow's wind forecast *does* predict today's outcomes,
    which we interpret as intertemporal dependence rather than a failed placebo: d+1
    weather forecasts exist at gate closure, and hydro and unit commitment are
    intertemporal. Conditioning on it (Table 9) cuts wind's novelty effect by 60% and
    leaves solar unchanged.
- **(f) Novelty conflates amplitude and timing: Done.**
  - Rank novelty and peak and trough timing shifts are in Table 3. Solar's effect is
    unchanged by rank, and solar moves both peak and trough towards the typical hours.
  - The Figure 3 discussion (formerly Figure 1) is rewritten. It now says that neither
    example day has an unusual shape, and that the figure illustrates amplitude. We kept
    the mechanical, pre-specified selection rather than choosing new days after seeing
    results.

### M6. H4 rests on one zone: Done

Table 7 reports:

- H4 without DK_1 and without both Danish zones;
- the effect at DK_1's K, with its standard error (−0.94, s.e. 0.34);
- tercile slopes, where high minus low is +1.07 (p = 0.81).

The text says H4 is driven by DK_1, and the "lottery" line is deleted.

### M7. Pre-registration adherence and disclosure: Done

- **The 14-day check** is run (Table 10).
- **Deviation timing** is stated accurately.
- **The false basis of deviation 4** is corrected in the correction log.
- **The "19 clusters" slip** is corrected in the correction log.
- **The code-change question** is answered in Appendix A. In commit `8e1dc7f` every change
  to `results.py` was figure code; no estimation code changed.
- **Exploratory material is labelled.** The FE build-up, the per-standard-deviation
  comparison, the ratio-noise gloss (deleted) and the placebo reading (now a conjecture)
  are all marked.

### M8. Robustness used selectively: Done

- **Section 6 presents all rows symmetrically,** with the range of estimates and
  p-values and a count of registered checks above and below 0.10.
- **The interpretive gloss is deleted.**
- **Two points are now stated explicitly:** leave-one-out stability is weak evidence,
  and the crisis exclusion reflects leverage, not the sign.
- **The pre-MTU sample is in Table 10.**

## Minor concerns

1. **CET offsets:** corrected; year-round, and including GR and EE.
2. **GB coverage:** "after 2020" everywhere.
3. **FC in the operator table:** added, with the 18:00 caveat.
4. **Table formatting:** three decimals for novelty, "<0.001" in place of "0.000".
5. **Star conventions:** Tables 2 and 4 now carry notes on which p-values the stars use.
6. **Table 1:**
   - CZ wind now prints as "–" instead of "nan".
   - The FC window is noted.
   - Medians and value-weighted capture are added.
   - The floor wording is corrected.
7. **Zone counts:** 18 zones in every regression, 19 in the descriptives. The zone table
   is now grouped by geography.
8. **"All four Nordic and Baltic zones":** corrected.
9. **Per-standard-deviation effect of an insignificant coefficient:** removed.
10. **H4 centring:** now at the estimation-sample mean, 18.36, as stated.
11. **The attenuation claim:** deleted.
12. **Sioshansi et al. (2009):** the literature review and introduction no longer imply
    novelty for the typical-day rule. We could not access the full text to verify the
    exact backcasting figures, so we cite the precedent without quoting them.
13. **Ketterer (2014):** distinguished as day-to-day, not intraday, volatility.
14. **Falezza (2026):** the benchmark is noted as not comparable, and rank novelty is
    added.
15. **Missing literature:** Bushnell & Novan, Cullen, Novan, Rintamäki et al., Wozabal et
    al., MacKinnon & Webb, and MacKinnon, Nielsen & Webb are added and verified.
16. **FE build-up numbers:** −9.65 and −8.75 are now attributed to the correct columns.
17. **The "sunny across Europe" speculation:** replaced by the statement that we have not
    tested which common shocks the date effects absorb.
18. **Redundancy:** the conclusion now interprets the findings rather than repeating them.
    The data section is renamed "Data and design".
19. **Quantile regressions: done (Table 11).** We use the two-step estimator of Canay
    (2011), with a pairs cluster bootstrap. The wind-minus-solar difference is −4.66 at
    the lower quartile, −2.10 at the median and −0.59 at the upper quartile. None is
    significant, so the mean result comes from the lower tail. The paper notes the
    estimator's caveat with 18 zones per date effect.
20. **Negative-price days:** the exclusion is reported for scale and capture (Tables 10 and
    11).

## Code

1. **The bootstrap** is fixed (M4).
2. **Singleton fixed effects:** not changed. The mismatch (4 observations) is immaterial,
   as the referee notes.
3. **The `panel_data.py` docstring** is corrected.
4. **The log V\* drop** is disclosed.
5. **The H4 centring** is fixed.
6. **The rolling window** is now time-based (`rolling("28D", closed="left")`).
7. **Partial-coverage shares** are now masked. The forecaster was re-run after items 6
   and 7.
8. **The look-ahead audit** is noted with thanks.
