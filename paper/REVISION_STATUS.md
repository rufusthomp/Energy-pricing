# Revision status (2026-10-17)

## Current state

- **Latest draft:** `paper/drafts/v3_referee_requests.pdf` (36 pages).
- **Earlier drafts:**
  - `v2_revised.pdf`: the rewrite after review.
  - `v1_first_draft_pre_referee.pdf`: the first draft.
- **Title:** "More Value, Not More Information: Wind, Solar and the Returns to Electricity
  Storage Arbitrage in Europe".
- **Referee report:** `paper/referee_report.md`.
- **Point-by-point response:** `paper/response_to_referee.md`. Every major and minor
  concern is now done, or done as far as the data allow.
- **Table files** are numbered in print order (`t01`–`t15`).

## Added in v3 (all exploratory)

- **Shape forecaster.** `gbm_shape` (migration `c3e5a7b9d1f2`;
  `panel_forecast --target shape`) is trained on the within-day price shape. Daily rank
  correlations are stored in `data/derived/forecast_rank_*.parquet` (Table 6). Re-running
  `gbm_forecast` with the modified code reproduced all 159,747 stored revenues exactly.
- **Weather instruments.** The `weather` schema (migration `d4f6b8c0e2a3`) holds 105
  ERA5 points, curated in `ingest/weather_points.py`, with 7.19M hourly rows.
  - `analysis/weather_days.py` builds the zone-day instruments.
  - `results.weather_iv` runs 2SLS (`iv_2sls`, validated against pyfixest) and reduced
    forms with WCB p-values (Table 15).
  - Every point was reverse-geocoded to its country. One misplaced Swiss point was moved.
- **Quantile regressions.** Two-step estimator of Canay (2011) with a pairs cluster
  bootstrap (Table 11).
- **Documentary research.** Load netting and forecast timing are covered in
  `docs/tso-forecast-practices.md`, verified against sources. One overstated claim, about
  SMARD, was corrected.

## What v3 changes in the findings

Nothing in the conclusions changes. The weather instruments support every result, and
make one sharper: the calendar operator's euro shortfall falls with solar. The shape
forecaster beats the registered forecaster overall, but its gain over the calendar
still does not rise with wind.

## Possible next steps

- A second referee pass on v3. An independent reader, not the author, should do it.
- Archived NWP forecasts issued before the auction, in place of realised weather.
- Intraday market prices.

## Rebuild

    python -m gbmo.arbitrage.panel_forecast --target shape
    python -m gbmo.ingest.weather_panel        # ~2 days of free-tier quota from empty
    python -m gbmo.analysis.weather_days && python -m gbmo.analysis.panel_data
    python -m gbmo.analysis.results            # everything (slow)
    python -m gbmo.analysis.results --extra weather shape quantile   # named steps only
    python paper/build.py
