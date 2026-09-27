# Revision status (paused 2026-09-27 ~16:00, usage limit)

## Done
- Referee report: paper/referee_report.md (major revision).
- Bootstrap bug fixed (estimate.py); reproduces the referee's corrected H1 p = 0.120.
- All revised analyses run: paper/tables/t1-t9, paper/results.json. Forecaster re-run with fixed features.
- 14-day TD check run (registered). Seven new references verified (references.bib).
- Sections 02 (literature), 03 (data/design) and 07 (appendix) are rewritten for the revision.

## Still to do (in order)
1. Check `python -m gbmo.analysis.results --extra` finished (t10_lead.md). If not, rerun it.
2. Rewrite sections 01 (intro), 04 (results), 05 (robustness), 06 (conclusion) and the
   abstract in metadata.yaml. Sections 01/04/05/06 still hold the FIRST-DRAFT text and numbers.
   Suggested new title: "More Value, Not More Information: Wind, Solar and the Returns to
   Electricity Storage Arbitrage in Europe".
3. Fix the table references in 07_appendix.md to the final table order.
4. `python paper/build.py`, render, check, and copy to paper/drafts/v2_revised.pdf.

## The corrected findings (source: results.json and tables)
- H1 (TD capture, wind − solar): −4.36, WCB p = 0.120; CV3 p = 0.147; Rademacher-enumerated p = 0.116. NOT significant.
- Scale: solar raises V* (log +0.249, p < 0.001). Robust to log(1+V*), €, zone×year×month,
  fixed denominator, no negative-price days, and tomorrow's forecasts. Region×date shrinks it
  to 0.148 (p = 0.009). Wind: never significant.
- Mechanism: solar makes shape more typical, wind less. Robust to rank novelty and region×date.
  Solar also aligns peak and trough timing with the typical day.
- Value of information (€): TD's shortfall (~€31/MW/day) does not move with wind or solar. The
  forecaster's gain over TD FALLS on windy days (−0.78 pp, p = 0.003). The message is "more
  value, not more information".
- Lead test (t4, t10): tomorrow's wind forecast predicts today's outcomes. It is not a valid
  placebo (d+1 weather forecasts exist at gate closure; hydro and commitment are intertemporal).
  Conditioning on it, solar effects are unchanged, and wind's novelty effect falls 60%
  (0.013 → 0.005). Wind acts through multi-day regimes; solar acts day by day.
- H4 is driven by DK_1 alone (without DK_1: p = 0.63).
- The forecast-error placebo fails for novelty (p = 0.015); elsewhere it is too imprecise to be informative.
