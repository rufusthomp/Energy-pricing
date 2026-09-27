# Referee report

**Manuscript:** "Is the Sun a Clock? Renewable Composition and the Value of Information in
Electricity Storage Arbitrage" (working paper, September 2026)

**Materials reviewed:** `paper/build/paper.md` (line numbers below refer to this file unless
stated), `paper/metadata.yaml` (abstract), `paper/tables/*.md`, `paper/results.json`,
`docs/preregistration.md` and its git history, `src/gbmo/arbitrage/{panel,panel_forecast,lp}.py`,
`src/gbmo/analysis/{panel_data,estimate,results}.py`, `paper/literature.md`,
`paper/references.bib`.

**Replication note.** I re-ran parts of the analysis on the authors' own analysis frame
(`data/derived/panel_days.parquet`), using read-only queries against the project database
for daily price extremes. My bootstrap reproduces every WCB p-value I checked in
`results.json` to four decimals with the authors' seed (H1 0.0985, PS 0.0295, FC 0.0679,
H4 0.0196, novelty placebo 0.0143, TD solar 0.1565), so the discrepancies reported below
come from the specification or the implementation, not from my replication. Unless marked
WCB, standard errors in my additional results are zone-clustered (CRV1) with the paper's
fixed effects.

---

## 1. Summary of the paper

The paper backtests a price-taking 1 MW / 2 MWh battery in 19 European day-ahead bidding
zones (2019 to 2026) under four information sets: perfect foresight (the ceiling V\*), a
28-day "typical-day" (TD) profile, persistence, and a gradient-boosted forecaster. It regresses
capture shares, log V\*, a shape-novelty index (1 − Pearson correlation of the day's prices
with the TD profile) and the daily spread on TSO day-ahead forecast wind and solar
penetration, with zone×year, zone×month and date fixed effects and 18 zone clusters. The
headline findings are that solar raises V\* (+28% per 10 pp) and wind does not; that solar
makes price shapes more typical and wind less typical; and that the pre-registered key
test (H1: β_w < β_s for TD capture) has the predicted sign, −4.36 pp per 10 pp, with a WCB
p-value of 0.099. The paper concludes that solar-created storage value is "public" and
wind-created value is "informational", and titles itself accordingly.

## 2. Recommendation: major revision

The project has real strengths: a transparent, code-generated pipeline; a genuine
pre-registration with a timestamped deviation log; a sensible operator ladder; and an
honest statement in Section 5.4 that H1 is marginal. But the paper's central claim is not
supported by its own evidence, and my checks turned up problems that change the
inference. (i) The wild cluster bootstrap is implemented incorrectly for fixed effects that
are not nested within clusters. Correcting it moves the key p-value from 0.099 to 0.120,
and it raises every other WCB p-value I checked. (ii) The pre-registered capture-share
outcome is dominated by one zone (NO_2), whose 5th-percentile "floor" is €0.82 per day. (iii)
In euro terms the TD result is a pure scale effect: solar raises V\* and TD revenue by the
same amount, and neither technology changes the calendar operator's absolute shortfall.
(iv) The paper's own forecaster *loses* ground to the calendar operator on windy days, which
directly contradicts the "wind value is informational" thesis. (v) The H4 heterogeneity
result rests on a single zone (DK_1). Several factual statements about the data are also
wrong (zero-value days, "perfectly flat" prices, the fixed-effect structure). A credible
paper could be built from what the data do show: solar raises arbitrage value and makes
price shapes more regular, and the calendar operator captures essentially all of that
increment. That paper needs a new title, a new abstract and conclusion, the corrected
inference, and a direct test of the value-of-information claims. That is more than a minor
revision, but the underlying work is salvageable.

---

## 3. Major concerns

### M1. The framing claims far more than the pre-registered test supports

**Problem.** The registered key test is H1. Its WCB p-value is 0.099 as reported and 0.120
once the bootstrap is corrected (M4). The decomposition also contradicts the registered
mechanism. The pre-registration says "Wind lowers typical-day capture more than solar
does" (preregistration.md, H1 row). Instead the wind coefficient is −0.21 (WCB p = 0.72), and
the whole difference comes from solar *raising* capture, which the paper itself concedes
(lines 494–496). Yet the title asks "Is the Sun a Clock?". The intro and the conclusion both
answer "The sun, in short, behaves like a clock" (lines 74, 727). The abstract states "Storage
value created by solar is largely public; value created by wind increasingly rewards
forecasting". The implications section asserts that "forecasting capability confers little
advantage" in solar systems and that "the returns to forecasting rise with wind's share"
(lines 732–741). None of these claims is tested:

- No regression has the value of information (FC − TD, or PF − TD in euros) as the outcome.
- The one relevant piece of evidence goes the other way (M2).
- The wind half ("whether the wind behaves like a lottery depends on how much of it a
  system has", lines 74–75, 727–728) rests on H4, which is one zone (M6).

Further overstatements:
- Line 62–63 says the novelty mechanism "is precisely estimated". The novelty placebo
  fails (Table 4).
- Line 66 says the H1 magnitude "is stable across every robustness check and every
  leave-one-zone-out fit". The leave-one-zone-out estimates range from −3.08 to −6.45, a
  factor of two, and one registered robustness check is missing (M7).
- Line 86–87 claims a design "robust to the common trends that have undermined
  time-series evidence". The design is not robust to regional common shocks (M5b).
- The abstract says "treatments vary with weather alone". That is not what the fixed
  effects deliver (M5a), and the treatments are partly load (M5c) and partly post-auction
  information (M5d).

**Why it matters.** A reader of the title, abstract and conclusion would come away
believing that a pre-registered test confirmed the hypothesis. It did not. The paper's
contribution then rests on H3, which had no registered direction, and H2.

**Fix.**
- Retitle and rewrite the abstract, intro bullets and conclusion. Label every claim as
  confirmatory or exploratory: H1 inconclusive; H2 confirmed, with the placebo caveat; H3
  exploratory in direction; H4 confirmed but driven by one zone.
- Delete the public/informational policy implications, or test them directly (M2).
- Drop "the sun behaves like a clock" as a stated finding.

### M2. The paper's own forecaster contradicts the value-of-information thesis

**Problem.** The thesis is that wind creates value "available only to operators who
forecast" (line 22). If so, the forecaster should lose *less* capture on windy days than
the calendar operator. Table 2 shows the opposite: the wind coefficient is −0.98 for FC and
−0.21 for TD. Regressing the within-day advantage of the forecaster directly on the
treatments (main specification) gives:

| Outcome | β wind (per 10 pp) | β solar (per 10 pp) |
|---|---|---|
| cap_FC − cap_TD (pp) | −0.77 (0.18) | −0.46 (0.58) |
| V_FC − V_TD (€/MW/day) | −0.66 (0.22) | +0.99 (0.60) |

The return to day-specific fundamentals therefore *falls* on windy days, and the estimate is
precise. This is the most direct test of the paper's policy claims, and it rejects them.
Separately, the paper and the pre-registration (deviation 3) call FC − TD "exactly the value of
day-specific information". But FC underperforms TD in FI, SE_3, SE_4 and EE (Table 1; text
lines 407–408). A forecaster trained on squared price-deviation loss need not dominate TD in
arbitrage revenue, so FC − TD measures how well this one model uses the information, not
what the information is worth. The statement "Day-specific information is therefore worth
2.6 points" (lines 402–403) should be qualified in the same way. The 2.6 is also a difference
of means over different samples: FC has 43,640 zone-days and TD 43,829, and FC starts in
May 2019 for DE_LU.

**Why it matters.** The policy argument about the market structure of flexibility, and about
TSO forecasts being "worth more to small operators", depends on the value of forecasting
information rising with wind. The only evidence in the paper points the other way.

**Fix.**
- Make FC − TD (in € and in pp) and PF − FC outcomes in Table 2, and run the H4 analogue
  on FC − TD.
- Use a decision-focused forecaster, or at least one tuned for rank accuracy, since
  Falezza (2026) shows rank correlation is what drives capture. Report its sensitivity.
- If the result stands, report it as a finding: at the day-ahead stage, TSO wind
  forecasts do not help a battery more on windy days.

### M3. The capture-share outcome is ill-conditioned, and in levels H1 is a scale effect

**(a) NO_2 dominates the outcome.** The zone-relative 5th-percentile floor on V\*
(`panel_data.py:113–124`) is €0.82 per day in NO_2, against €8 to €28 elsewhere. NO_2's
1st-percentile floor is €0.08. In NO_2 the TD capture share has a standard deviation of 259
pp and a minimum of −6,613%; 10.7% of its retained days have negative capture. The
within-sample variance of TD capture is 67,156 in NO_2 against 373 to 1,773 in every other
zone. So one zone supplies most of the outcome's variance, and that zone has no solar
variation at all: its solar forecast is identically 0 on all 2,810 days.

The text says Norway "identifies only the wind coefficient" (line 656). That is wrong. Through
the date effects NO_2's noise contaminates the solar estimate as well. Dropping NO_2 moves
β_s from 4.15 to 6.53 while β_w barely moves (results.json, `leave_one_out`).

**(b) Sensible alternative constructions give very different precision.** Estimates of
β_w − β_s for TD capture (zone-clustered SEs; all exploratory and computed after seeing
results):

| Construction | β_w − β_s (SE) |
|---|---|
| Registered (5th-pct floor) | −4.36 (2.59) |
| Drop NO_2 | −6.45 (1.44) |
| Capture clipped to [−100, 100] | −5.57 (1.46) |
| V\*-weighted | −3.84 (0.69) |
| Absolute floor V\* ≥ €20 | −5.89 (1.28) |

I do not suggest promoting any of these to the headline, which would be a forking-paths
exercise. The point is that the registered outcome was badly conditioned. The paper should
say so plainly. It currently offers the softer reading that "imprecision comes from ratio noise
on low-value days rather than from fragility in the sign" (lines 661–662).

**(c) In euros the result is mechanical.** A capture share rises whenever V\* rises and the
TD operator's absolute shortfall does not. That is what happens here:

| Outcome (€/MW/day unless noted) | β wind | β solar |
|---|---|---|
| V\* | −3.21 (2.13) | +47.7 (6.7) |
| V_TD | −2.71 (1.67) | +49.3 (6.3) |
| Shortfall V\* − V_TD | −0.50 (0.55) | −1.55 (1.24) |
| log V_TD | −0.024 (0.018) | +0.309 (0.054) |

Solar raises V\* and TD revenue by the same amount. Neither technology moves the calendar
operator's absolute shortfall (difference p ≈ 0.46). The share result (H1) is therefore close
to a restatement of H3 plus a constant euro shortfall. One could still argue that the
marginal solar value is fully capturable from the calendar, and that is the defensible core
of the paper. But wind creates no extra shortfall at all, so there is no "informational"
wind value to explain.

**(d) Undisclosed sample loss in log V\*, and false statements about zero-value days.**
- The frame contains **1,204** zone-days with V\* = 0 across **14** zones: NO_2 609, PT 103,
  ES 100, SE_3 85, GR 69, SE_4 50, PL 39, CH 34, FI 33, DK_1 29, DK_2 24, EE 17, IT_NORD 8,
  AT 4.
- Deviation 4, Appendix A (lines 787–789) and the `ratio_keep` docstring all state that
  only NO_2 has zero-value days and that they have "perfectly flat prices". Both statements
  are false.
- None of the 1,204 days has a zero spread. In NO_2 the spread on zero-value days has a
  median of €4.39 and a maximum of €73.6. V\* = 0 simply means no intraday spread
  exceeded the 15% round-trip loss.
- Line 349 ("22% of days have perfectly flat prices") repeats the error.
- As a result, the positive-days floor rule changes the floor in 14 zones, not one.
- log V\* silently drops these days: N = 45,876 against 46,884 for novelty and spread,
  which is 1,008 days within the estimation sample. The text never mentions this.
- Reassuringly, the drop is innocuous. log(1 + V\*) gives β_s = 0.245 (0.060). A linear
  probability model for V\* = 0 shows no treatment effect (β_w −0.001, β_s 0.001).
- Fix: disclose the drop, correct the factual statements, and report log(1 + V\*) or
  Poisson-PML in levels.

**Fix for the construct as a whole.**
- State in advance, as a new registered amendment, a decomposition:
  log V_TD = log V\* + log(share).
- Report the euro shortfall and the value-weighted capture (ΣV_TD / ΣV\* by zone-month).
- Retain the registered share as one row, with its known ill-conditioning explained.

### M4. The wild cluster bootstrap is mis-implemented, and correcting it weakens every result

**Problem.** `estimate.py:42–82` bootstraps on FE-demeaned data. The code builds
y\* = fitted_r + u_r ⊙ w, where w is the Webb weight for each zone cluster, and regresses y\*
on the demeaned X without demeaning y\* again. The docstring (lines 8–10) claims
Frisch–Waugh–Lovell makes this equivalent to bootstrapping the full model. That holds for
β\* only, because X is orthogonal to the fixed-effect space, so X′y\* = X′M_D y\*. It does not
hold for the bootstrap residuals that enter the cluster-robust variance.

The date effects are not nested within zone clusters. So u_r ⊙ w is no longer orthogonal to
the date dummies, and a correct bootstrap removes that component by refitting the fixed
effects on y\*. The code leaves it in, which distorts the denominator of every bootstrap t
statistic. The fix costs almost nothing. Because M_D is linear, M_D(u_r ⊙ w) =
Σ_g w_g M_D(u_r ⊙ 1_g). Precompute the G = 18 demeaned vectors once, and each draw
is a linear combination.

**Consequence** (same seed, 9,999 draws, identical otherwise):

| Test | WCB p as coded (= results.json) | WCB p re-demeaned |
|---|---|---|
| H1: TD capture, β_w − β_s | 0.0985 | **0.1197** |
| TD capture, β_s | 0.1565 | 0.1857 |
| PS capture, β_w − β_s | 0.0295 | 0.0415 |
| FC capture, β_w − β_s | 0.0679 | 0.0879 |
| H4 interaction | 0.0196 | 0.0273 |
| Novelty placebo (error) | 0.0143 | 0.0148 |

The corrected H1 is not significant at 10%. The abstract's "(p = 0.10)" and the "*" in Table
2 column 1 both need to change.

**Other inference issues.**
- *Few effective clusters for solar.* NO_2 has no solar variation, and FI (mean 1.1%), SE_3
  (1.6%) and SE_4 (3.6%) have little. Heterogeneous, high-leverage clusters are exactly the
  setting where wild cluster bootstraps are known to be unreliable (MacKinnon & Webb 2017,
  *J. Applied Econometrics*; MacKinnon, Nielsen & Webb 2023, *J. Econometrics*). Please
  report:
  - cluster leverage and partial leverage for each coefficient;
  - CV3 / jackknife standard errors;
  - the Rademacher WCB with full enumeration, which at G = 18 means 2^18 = 262,144
    draws and is feasible.
- *Cross-cluster dependence.* Zones are not independent units under market coupling.
  Neighbouring zones' residuals on the same date are correlated beyond what date effects
  remove (see M5b). Two-way clustering by zone and date handles same-date correlation, but
  only with conventional, not bootstrap, p-values. It also gives a smaller SE than one-way
  clustering (2.52 against 2.59), which is a warning sign about how well the variance is
  estimated, not reassurance. Consider region-level clustering with randomisation
  inference, or a cross-sectional (Driscoll–Kraay type) correction.
- *Webb weights.* The citation (line 165) argues that six-point weights beat Rademacher for
  G below about 12 (literature.md). At G = 18 the choice is harmless, but it does not address
  the actual problem, which is heterogeneous clusters.

### M5. Identification threats that are unaddressed or mis-described

**(a) The fixed effects are not what the text says they are.** Lines 48–49 and 315 (and the
abstract) describe the residual variation as "day-to-day weather within a zone-year-month".
The specification (`estimate.py:17`) is additive zone×year + zone×month. It does not remove
zone-year-month means. Additive zone×month effects are held fixed from 2019 to 2026, so they
cannot absorb a solar seasonal amplitude that scales with installed capacity, which roughly
triples over the sample. Symptoms:
- The pooled TD-capture solar coefficient (4.15) lies below both sub-period estimates:
  10.3 (3.9) for 2019–22 and 5.4 (1.9) for 2023–26.
- With zone×year×month + date effects:

  | Outcome | β_s |
  |---|---|
  | TD capture | 6.88 (2.08) |
  | log V\* | 0.288 (0.044) |
  | Novelty | −0.062 (0.009) |

The direction happens to favour the authors, but the text must describe the registered
specification accurately, and the specification is fragile to a natural refinement.
Zone×week-of-year effects leave the results roughly unchanged (TD solar 4.42 (3.11)), so
within-month day-length trends are not the issue. Capacity-scaled seasonality is.

**(b) Market coupling and regional common shocks.** Date effects absorb only the component
common to all 19 zones. Replacing them with region×date effects (Nordic/Baltic; CWE + CZ,
PL; Iberia; GR + IT_NORD) gives:

| Outcome | β_s, date FE | β_s, region×date FE |
|---|---|---|
| log V\* | 0.249 | 0.148 (0.051) |
| Novelty | −0.051 | −0.037 (0.013) |

H1 becomes −3.54 (2.97). A large part of the identifying variation is therefore *between
regions on the same day*. For example, sunny Iberia is set against a cloudy, hydro-priced
Nordic region, and those regions differ in marginal technology, interconnection and
congestion, not only in weather. The paper acknowledges spillovers only verbally (lines
156–158, 687–690) and reinterprets the coefficient as "weather in a zone's region". Under
that reinterpretation, the date-effect comparison across regions is exactly what is not
weather-driven.

Fix: report region×date effects as a main robustness check. Add neighbours'
(interconnection-weighted) forecast penetration as a spatial lag. Discuss the SUTVA
violation explicitly.

**(c) The denominator moves with weather.** Penetration is forecast output over forecast
load. Regressing log forecast load on the treatments gives β_s = −0.045 (0.007) per 10 pp.
Sunny days have lower forecast load, plausibly because several TSOs net embedded PV out of
their load forecasts, and because of temperature. So solar_pen mixes the solar numerator with
a load denominator that is itself a demand-side treatment. The conclusions survive the checks
below, but they belong in the paper:
- A fixed-denominator treatment (forecast output over the zone-month mean load) gives TD
  β_s 5.36 (2.76), log V\* 0.261 (0.048) and novelty −0.053 (0.010).
- Adding log load as a control changes little.

Please document which TSOs publish load net of embedded generation.

**(d) Forecast timing, and possible endogeneity of the treatment.** The paper says the
treatments are "the information on which the auction clears" (lines 45–46, 222–224), and the
placebo logic depends on this (lines 331–334, 571–572). Yet line 681 concedes that
Regulation 543/2013 requires wind and solar forecasts only by 18:00 on D−1, after the 12:00
auction. Lines 684–685 then assert that this "does not affect" the treatments because they
are "regressors rather than operator inputs". That is a non sequitur. If published forecasts
include post-auction updates, the treatment contains information the auction did not have,
and the placebo's premise fails.

Worse, some TSO renewable forecasts may be net of expected market-based curtailment at
negative prices, which would make the "forecast" a function of the price. Solar raises the
probability of a negative-price day by 8.6 pp per 10 pp (0.020), and negative-price days
make up 17% to 20% of zone-days from 2024 onward. (Reassuringly, excluding negative-price
days leaves log V\* β_s at 0.263 (0.063). The authors should report this.)

Fix:
- Establish publication timestamps per TSO. ENTSO-E document metadata carry creation
  times.
- Use only vintages published before 12:00, or instrument forecast penetration with
  numerical-weather-prediction or reanalysis weather (irradiance, 100 m wind speed). That
  would turn "identification from weather" into literal truth.

**(e) The placebo is under-powered, and its failure is explained away.**
- Where the placebo "passes" (lines 575–578), it passes because it is imprecise.
  - For the spread, the error coefficient (−2.53) is as large as the forecast coefficient
    (−2.94).
  - For TD capture, the error's 95% CI of about [−0.72, 0.81] contains the forecast
    effect.
  - A test that cannot distinguish the placebo from the treatment is not evidence for the
    timing.
- The measurement-error explanation of the novelty failure (lines 599–610) is untested.
- The claim that wind coefficients elsewhere "are, if anything, attenuated" does not follow.
  With fixed effects, two correlated mismeasured regressors and an error term that proxies
  for market information, the direction of bias is not signed. That is especially true for
  the difference β_w − β_s.
- An equally plausible alternative is that large forecast errors happen on frontal or
  transition days, whose price shapes are atypical for reasons the market knew.
- The registered placebo covered "every outcome above", which includes PS capture, but
  Table 4 omits it.

Fix:
- Report equivalence (TOST) tests, with bounds set at the forecast coefficient.
- Add a lead placebo (D+1 forecast penetration, which cannot affect day d's auction).
- Add the omitted outcomes.
- Present the measurement-error reading as a conjecture.

**(f) Novelty conflates amplitude with timing.** Pearson correlation with a fixed-shape
profile rises mechanically when the common diurnal component is large relative to
idiosyncratic noise. Solar widens the spread by €22 per 10 pp and wind narrows it, so part of
"solar makes the shape more typical" is "solar makes the shape bigger". As a diagnostic
only (log spread is a bad control), adding log spread moves β_s on novelty from −0.051 to
−0.043 and β_w from 0.013 to 0.011.

Figure 1 undercuts the narrative. On the windiest DE_LU day (24 Nov 2024) novelty is 0.086,
far *below* the mean of 0.22, and TD capture is 85.4%. On the sunniest day, novelty is 0.088
and capture 85.5% (results.json, `examples`). The text says "the typical evening peak simply
did not happen" (lines 387–388), but the windy day's price shape correlates 0.91 with the
typical profile. The two example days are indistinguishable on the paper's own mechanism
variables. They illustrate only the level effect: V\* was €33 against a DE_LU 2024 mean of
€208.

Fix:
- Use a rank-based novelty (Kendall or Spearman, matching Falezza 2026, whom the paper
  cites as the analogue) and a timing measure, such as the distance between the actual and
  typical hours of the daily minimum and maximum.
- Rewrite the Figure 1 discussion, or choose illustrative days by novelty rather than by
  penetration.

### M6. H4 rests on one zone

K is the zone-year mean of wind penetration. DK_1 is the only zone with K above 38: its
zone-years run from 51% to 66%, and the next highest is DK_2 at 20% to 38%. Re-estimating H4:

| Sample | Interaction (SE) |
|---|---|
| All zones (as reported) | −0.350 (0.080) |
| Without DK_1 | −0.412 (0.403) |
| Without DK_1 and DK_2 | +0.230 (0.467) |

The claim that wind's cost "appears clearly in wind-dominated zones like Denmark" (lines
70–72) is a linear extrapolation to K ≈ 58, presented without a standard error (lines
557–558). At DK_2's K of about 29 the implied effect is roughly +0.1, so "zones like
Denmark" means one zone. The conventional t of about 4.4 against a WCB p of 0.02 (0.027
corrected) is itself the signature of a single high-leverage cluster. Adding solar×K does
not change the wind interaction (−0.37), but solar×K is sizeable too, at −0.95 (0.65).

Fix:
- Report H4 leave-one-zone-out results.
- Report the effect at DK_1's K with a standard error.
- Report a non-parametric version, for example by terciles of K.
- Describe the result as "driven by DK_1", and remove the "lottery depends on how much of
  it a system has" line from the abstract, intro and conclusion.

### M7. Pre-registration adherence and disclosure

- **A registered robustness check is missing.** The pre-registration lists "A 14-day TD
  window". Table 5 omits it, while line 614 claims Table 5 "reports every robustness check
  fixed in the pre-registration". The git commit message for the results (8e1dc7f) makes
  the same claim ("magnitude stable across all robustness rows").
- **Deviation timing is overstated.** Deviations 4 and 5 were logged in commit 316c164
  (13:28, 27 Sep 2026). By the log's own account they were "found in the frame's summary
  statistics", after V\* (an outcome) had been computed. That commit also adds
  `estimate.py` and `results.py`.
  - Lines 88 and 336 say everything was registered "before any panel outcome was
    computed". That is true of the original registration but not of these deviations. Say so.
  - The factual basis of deviation 4 is wrong (M3d).
- **Code changed alongside the first results.** `results.py` changed by 104 lines in the
  same commit as the first results (8e1dc7f), and the draft sections were committed at 13:33,
  before any results existed. Please state what, if anything, changed in the analysis code
  after the first estimates were seen.
- **Registered text and paper disagree.**
  - The pre-registration refers to "19 clusters" (preregistration.md line 89).
  - The registered hypothesis text predicted wind would "raise [value], or reshape it".
    Wind does not raise value, and the paper should say this part of the hypothesis
    failed.
- **Exploratory material presented as confirmatory.** The FE build-up narrative (lines
  517–524), the "ratio noise" interpretation (lines 641–662), the measurement-error reading
  of the placebo, and the per-standard-deviation comparisons are all exploratory. Mark them
  as such.

### M8. Robustness is used selectively to argue past the registered p-value

Lines 641–647 quote the favourable variants: p = 0.008 excluding the crisis and 0.029 with
the 10th-percentile floor. Section 6.2 then concludes that the imprecision "comes from ratio
noise … rather than from fragility in the sign". Three problems:
- Leave-one-zone-out sign stability is weak evidence, because every estimate shares 17 of
  18 clusters.
- Excluding the crisis removes 28% of zone-days yet cuts the standard error by 37%. That
  shows the crisis days are high-leverage outliers in the ratio. It says nothing about the
  sign.
- The 15-minute MTU year (October 2025 onward) also matters. Pre-October-2025 data give
  −3.79 (2.79) for H1.

Present robustness symmetrically, and drop the interpretive gloss.

---

## 4. Minor concerns

1. **The CET offsets are misstated** (line 216). "In summer, Portugal and Ireland begin their
   trading day at 23:00 local time and Finland at 01:00." EU daylight saving is
   synchronised, so these offsets hold all year. Greece and Estonia (EET) also start at
   01:00. Ireland is not in the sample. (Code check: every panel zone uses
   `market_timezone = Europe/Brussels`, so the day definition is consistent across
   operators, profiles and outcomes. That part is correct.)
2. **GB coverage is described three ways.** Line 206 says it "ends in 2020–21"; the
   pre-registration says "no ENTSO-E coverage after 2020"; `panel.py:39` says "no ENTSO-E
   prices after 2020". Reconcile them.
3. **The operator table (lines 264–268) lists PF, TD and PS only.** FC appears in the intro,
   Table 1 and Table 2 but is defined only in Appendix B. Add it to the table with its
   information set and the 18:00 timing caveat.
4. **Some Table 2 cells are uninformative.** The novelty column is printed to two decimals:
   "0.01*** (0.00)". Use three. Report "[<0.001]" rather than "[0.000]"; the minimum
   attainable p is 0.0001.
5. **Tables 2 and 3 use different stars.** Table 2 stars use WCB p-values, Table 3 stars
   conventional ones. The same −4.36 carries a star in Table 2 and none in Table 3. Use one
   convention, or flag the difference prominently.
6. **Table 1 needs cleaning.**
   - It prints "nan" for CZ wind.
   - FC means use a shorter window for DE_LU (from May 2019).
   - "Days" counts all days, while the capture means use floor-filtered subsets.
   - The capture means are unweighted and dominated by the left tail. NO_2's 17.5% is the
     mean of a distribution with minimum −6,613%. Add medians and value-weighted capture
     (ΣV_TD / ΣV\*).
   - The note says "above each zone's 5th percentile of V\*", but the floor is computed
     among positive days only.
7. **Line 32 (and the abstract): "19 European bidding zones".** The regressions use 18.
   Also, line 33 cites "Iberian and Greek solar", while the zone table (lines 196–202)
   classifies PT and ES as "Wind-heavy".
8. **Lines 407–408: "In all four Nordic and Baltic zones (Finland, both Swedish zones and
   Estonia)".** The sample has seven Nordic/Baltic zones. DK_1, DK_2 and NO_2 show FC > TD.
9. **Line 455–456: "a windy day lowers it by 2.4%".** The underlying coefficient has
   p = 0.25. Do not report a per-standard-deviation effect of an insignificant coefficient
   as a directional finding.
10. **Line 555: "Evaluated at the panel mean (K = 18.4%)".** The interaction is centred at
    the mean of `k_wind` over all zone-days (17.76, `results.py:56`). The quoted 18.36
    (`results.py:244`) is the estimation-sample mean. The difference is tiny, about 0.02 pp,
    but the stated evaluation point is wrong.
11. **Lines 609–610.** The claim that other wind coefficients are "attenuated" is not
    implied by classical measurement error with fixed effects and correlated regressors (see
    M5e).
12. **Literature: Sioshansi et al. (2009) and the contribution claim.** To my recollection,
    Sioshansi et al. (2009) also evaluate a dispatch rule based on recent weeks' prices
    ("backcasting"). That rule is close to the TD operator, and they report that it captures
    a large share of the perfect-foresight value in PJM. If so, the contribution statement
    (lines 79–82) and the literature summary (line 102) understate the precedent. Please
    check and cite accordingly.
13. **Literature: Ketterer (2014).** Ketterer models *day-to-day* price volatility (GARCH on
    daily prices), not the intraday spread. Lines 128–129 ("volatility is the raw material of
    arbitrage") conflate the two, and the paper never reconciles its own finding that wind
    *narrows* the intraday spread with Ketterer's.
14. **Literature: Falezza (2026).** Falezza's persistence benchmark (about 33%) is from
    multi-market trading. This paper's persistence operator captures 64%. Note that the two
    are not comparable. Also, Falezza's lesson is about *rank* correlation, while the
    novelty index uses Pearson (see M5f).
15. **Missing literature.**
    - Bushnell & Novan (2021, *JAERE*, "Setting with the Sun") show solar reshapes the
      intraday price profile, lowering midday and raising shoulder prices. That is a direct
      precedent for the solar-spread result.
    - Cullen (2013, *AEJ: Policy*) and Novan (2015, *AEJ: Policy*) use weather-driven wind
      variation for identification.
    - Rintamäki, Siddiqui & Salo (2017, *Energy Economics*) find wind and solar affect
      daily and weekly price volatility differently in Denmark and Germany.
    - Wozabal, Graf & Hirschmann (2016, *OR Spectrum*) find non-monotone effects of
      renewables on price variance.
    - On inference: MacKinnon & Webb (2017, *JAE*) and MacKinnon, Nielsen & Webb (2023,
      *J. Econometrics*).
16. **Lines 519–520: "With only zone and season effects … the wind-minus-solar difference
    is then −8.75".** −8.75 is the column that also includes zone×year (Table 3, column 4).
    With zone and zone×month only it is −9.65.
17. **Lines 521–523.** "Much of the naive association comes from days that are sunny across
    Europe at once …" is untested speculation. Label it as such, or show it, for example by
    regressing the date effects on the cross-zone mean solar penetration.
18. **Redundancy.** The four findings appear almost verbatim in the abstract, intro (lines
    57–75) and conclusion (lines 712–728). The conclusion should add interpretation rather
    than repeat the bullets. The "Data" section also contains the operators and outcomes;
    rename it "Data and design".
19. **Identical schedules.** TD revenue equals V\* on 1.6% of zone-days, and TD equals PS on
    1.8%. That is not material. But the capture share is capped at 100 and unbounded below,
    so OLS means are driven by the left tail. Report quantile (median) regressions.
20. **Negative prices and the mechanical-V\* concern.** From 2024 onward, 17% to 20% of
    zone-days have a negative hour. The authors should report that the solar-V\* result
    survives excluding these days: β_s 0.263 (0.063) in my check. It strengthens the
    paper.

---

## 5. Numerical and text inconsistencies found

| Location | Text says | Source says |
|---|---|---|
| Abstract; Table 2 col. 1 star; line 723 | H1 p = 0.10 (0.099), significant at 10% | Correct WCB (re-demeaned) p = 0.120. The 0.099 comes from the bootstrap bug (M4) |
| Lines 519–520 | "only zone and season effects … difference is then −8.75" | Table 3: zone + zone×month gives −9.65; −8.75 also includes zone×year |
| Line 349; lines 787–789; prereg deviation 4; `panel_data.py:116–119` | NO_2's 609 zero-value days have "perfectly flat prices"; "No other zone has a zero-value day"; floor change "only for NO_2" | 1,204 zero-V\* days in 14 zones; none has zero spread (NO_2 median spread €4.39, max €73.6) |
| Table 2 note / text (log V\* N) | Not disclosed | log V\* drops 1,008 zero-V\* days from the estimation sample (45,876 vs 46,884) |
| Line 614 | "Table 5 reports every robustness check fixed in the pre-registration" | The registered "14-day TD window" check is absent |
| Lines 66, 637 | Magnitude "stable across every robustness check and every leave-one-zone-out fit" | LOO range −3.08 to −6.45 (results.json); one registered check missing |
| Line 656 | Norway "identifies only the wind coefficient" | Dropping NO_2 moves β_s 4.15 → 6.53 while β_w moves only −0.21 → +0.08 |
| Lines 48–49, 315; abstract | Residual variation is "within a zone-year-month"; "treatments vary with weather alone" | FE are additive zone×year + zone×month (`estimate.py:17`), not zone×year×month |
| Lines 387–391 (Figure 1) | Windy day: "typical evening peak simply did not happen" (atypical shape) | results.json `examples`: windy-day novelty 0.086 (mean 0.22), TD capture 85.4%, the same as the sunny day (0.088, 85.5%) |
| Lines 70–72, 557–558 | Wind's cost "appears clearly in wind-dominated zones like Denmark" | Only DK_1 (K ≈ 58). Implied effect at DK_2 (K ≈ 29) is ≈ +0.1. No SE given at K = 58. Without DK_1 the interaction SE is 0.40 |
| Line 555 | Evaluated at "panel mean (K = 18.4%)" | Centring constant is 17.76 (`results.py:56`) |
| Lines 407–408 | "all four Nordic and Baltic zones" | Seven Nordic/Baltic zones in sample; FC > TD in DK_1, DK_2, NO_2 |
| Line 32; abstract | 19 zones | 18 in every regression |
| Line 216 | Offsets "in summer" | Year-round; also applies to GR and EE |
| Line 206 vs prereg / `panel.py:39` | GB coverage ends "2020–21" | "after 2020" |
| Prereg line 89 | "With 19 clusters" | 18 |
| Lines 402–403 | FC − TD = 2.6 pts "day-specific information is worth" | Means over different samples (43,640 vs 43,829 zone-days); FC < TD in four zones |
| Lines 684–685 | Treatment timing issue "does not affect" treatments | Contradicts lines 45–46, 222–224 and the placebo premise (lines 331–334) |

Everything else I checked matches results.json and the tables:
- Descriptives: €153 and €56k, the more than threefold range, 73.4 / 64.0 / 76.0, and the
  zone FC − TD gaps.
- The 28% / €22 / −2.0% / 7.4% / 2.4% effects, and novelty +0.016 / −0.015.
- The placebo numbers, the robustness rows, and the H4 values of +0.9 / −0.9.

---

## 6. Possible code bugs

1. **`src/gbmo/analysis/estimate.py:63–81`, wild cluster bootstrap with non-nested FE
   (material).**
   - y\* = `fitted_r + u_r * w` is used without projecting out the fixed effects again.
     Since date FE cross zone clusters, M_D(u_r ⊙ w) ≠ u_r ⊙ w.
   - β\* is unaffected, but the bootstrap residuals `u = yv − X @ beta` (line 65) include
     P_D(u_r ⊙ w), which distorts each t\*.
   - The docstring claim at lines 8–10 is incorrect for this design.
   - Effect: H1 p goes from 0.0985 to 0.1197, and all six p-values I checked rise (M4 table).
   - Fix: precompute `V[g] = demean(u_r * 1{cluster==g})` for each of the 18 clusters, then
     set `y* = fitted_r + w @ V`.
2. **`src/gbmo/analysis/estimate.py:29–39` vs `:21–26`, sample mismatch (immaterial).**
   `demean` does not drop fixed-effect singletons, but pyfixest does; the build-up N falls
   from 43,833 to 43,829 when date FE enter. Singletons demean to zero, so the coefficients
   are unaffected, and the small-sample factor cancels in the bootstrap comparison. Worth
   aligning for cleanliness.
3. **`src/gbmo/analysis/panel_data.py:113–124` and docstring.** The logic is fine, but the
   documented premise ("Only NO_2 has zero-value days", "perfectly flat prices") is false.
   The positive-days floor changes floors in 14 zones. The relative floor also produces
   NO_2's €0.82 floor, which is the root of M3a.
4. **`src/gbmo/analysis/panel_data.py:183`.** `log(pf.where(pf > 0))` silently drops 1,204
   zero-value zone-days from the log V\* outcome. This is undisclosed; see M3d.
5. **`src/gbmo/analysis/results.py:56` vs `:244`, centring mismatch.** `wind10_x_k` is
   centred at `df["k_wind"].mean()`, the mean over all zone-days including those outside
   the estimation sample (17.76). The reported evaluation point is the estimation-sample mean
   (18.36). `kw_c` (line 55) is computed but never used, which suggests an intended
   within-zone centring was abandoned.
6. **`src/gbmo/arbitrage/panel_forecast.py:82`, rolling window over rows, not days.**
   `.rolling(28, min_periods=14)` runs over the rows of dates present in `df`, which are
   days with a TD profile. After data gaps the "28-day level" therefore spans more than 28
   calendar days. This is not a look-ahead leak: `.shift(1)` correctly excludes day d. Use a
   time-based window (`rolling("28D")` on a DatetimeIndex).
7. **`src/gbmo/arbitrage/panel_forecast.py:76–78`, partial-coverage shares.**
   `day_wind_share` and `day_solar_share` are ratios of sums over the available hours;
   pandas skips NaN in the sum. Days with partially missing forecasts get biased shares,
   whereas the regression treatments require full coverage. Mask these days, or require
   complete coverage, for consistency.
8. **Look-ahead audit (no leak found).** I checked `panel_forecast.py` and `panel.py`:
   - Training uses only days before the forecast month (line 106).
   - TD and PS profiles use days d−28..d−1 and d−1 (`panel.py:101–117`), which are
     known at gate closure.
   - The yesterday features are deviations of d−1 prices from d's TD profile.
   - Hyperparameters are fixed, not tuned.
   - The only information-timing issue is the one the authors disclose: VRE forecasts are
     published by 18:00 D−1. Its implications for the *treatments* are not handled; see
     M5d.
   - The vectorised TD profile in `panel_data.py:62–86` mirrors the operator (including
     the 20-of-28 rule and the `shift(1)`).
   - The LP (`lp.py`) matches the paper's formulation, and the binary exclusion is correctly
     implemented.
