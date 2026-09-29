# Revision status (2026-09-29)

## Current state
- **Revised draft:** `paper/drafts/v2_revised.pdf`. The first draft is kept as
  `v1_first_draft_pre_referee.pdf`.
- **Title:** "More Value, Not More Information: Wind, Solar and the Returns to Electricity
  Storage Arbitrage in Europe".
- **Referee report:** `paper/referee_report.md`.
- **Point-by-point response:** `paper/response_to_referee.md`. Every major and minor
  concern is marked done, partly done or not done, with reasons.
- **All sections are rewritten.** Table files are numbered in print order
  (`t01`–`t12`), so the text's "Table N" matches the file name.

## Referee requests not carried out (stated as limitations in Section 6)
- Forecast publication timestamps.
- A weather-data (NWP or reanalysis) instrument.
- Which TSOs publish load net of embedded generation.
- A decision-focused or rank-tuned forecaster.
- Median (quantile) regressions. The euro shortfall answers the same concern.

## Possible next steps
- A second referee pass on v2. An independent reader, not the author, should do it.
- A weather-data instrument for the treatments. This is the most valuable extension for
  identification.
- Intraday market prices, where any informational premium to wind should show.

## Rebuild
    python -m gbmo.analysis.results            # everything (slow: ~9,999-draw bootstraps)
    python -m gbmo.analysis.results --extra placebo heterogeneity   # named steps only
    python -m gbmo.analysis.results --figures
    python paper/build.py
