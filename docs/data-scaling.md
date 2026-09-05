# Data scaling and the dispatch storage decision

Written 2026-09-05, before the cross-country extension, to fix a decision that is
expensive to reverse once made.

## Where the size actually is

| | Size | Notes |
| --- | --- | --- |
| Git repository | **1.3 MB** | 693 KB of `.git` plus 635 KB working tree |
| Local data cache | 282 MB | gitignored, never travels |
| Postgres | **586 MB** | in a Docker volume, not the repo |

The repository is not and will not become the constraint. Everything below is about the
database.

| Table | Rows | Size | Bytes/row |
| --- | --- | --- | --- |
| generation | 3.37M | 255 MB | 76 |
| weather | 1.14M | 179 MB | **157** |
| dispatch | 842K | 79 MB | 94 |

Weather is expensive per row because the long format repeats `location`, `variable` and
`unit` as text on every row. That is the price of the store-as-observed convention, and it
is the reason weather must not be fetched for every country (see below).

## The projection

ENTSO-E covers roughly 35 countries at hourly resolution back to about 2015, so a decade
is around 3.1M country-hours.

| Choice | Rows | Estimated |
| --- | --- | --- |
| Mirror every production type (~15 fuels per country-hour) | 46M | ~3.5 GB |
| Store aggregates: price, load, VRE, total generation | 3.1M | ~250 MB |
| Per-period dispatch for every country, battery and strategy | 36.8M | ~3.5 GB |
| Daily run summaries instead | 1.5M | ~150 MB |

The dispatch line is the one that matters, because it grows every time a backtest is
re-run while source data is loaded once.

## The decision

**Source data stays at full resolution.** Half-hourly for GB, hourly elsewhere. The
forecaster trains on it and nothing about it is compressed.

**Backtest output is stored at daily grain outside GB.** One row per run-day carrying
revenue, energy throughput, cycle count, minimum and maximum state of charge, and the
validation result. Roughly a fortieth of the rows, and it keeps cycle and depth analysis
alive.

**GB keeps full per-period dispatch**, because that is where the deep work happens and
where intraday questions get asked.

**Weather is fetched only for countries the forecaster actually runs on.** Renewable
output comes from ENTSO-E directly, so the panel regression never needs weather; it is a
forecaster input, not a treatment variable.

## Why this does not cost any current analysis

Checked against the code rather than assumed. The only module that reads the `dispatch`
table per period is `gbmo.arbitrage.validate`, and it runs at write time, before any
aggregation would occur. `gbmo.arbitrage.forecast` reads `settlement_period`, `price`,
`demand`, `generation` and `weather`, and never `dispatch`.

| Analysis | Reads | Grain it needs |
| --- | --- | --- |
| Gradient-boosted and LSTM forecasters | source tables | half-hourly, unaffected |
| Day-level premium regression | daily revenue | daily |
| Cross-country panel | daily revenue | daily |
| Write-time invariant checks | per-period dispatch | runs before storage |

Daily is also the **correct** grain for the outcome rather than a compromise. Both
strategies optimise over a day with the store empty at both ends, so the sophistication
premium is defined per day. Splitting a day's advantage across its 48 periods would be
arbitrary.

The cross-country panel gains from this rather than losing: 35 countries by 3,650 days is
127,750 observations, against 2,425 in the current GB day-level analysis.

## What is genuinely given up

Intraday dispatch detail outside GB. Questions like *when* the forecaster's edge arises,
whether it comes from the evening peak or the overnight trough, or whether it trades more
often or better, need per-period rows. If those become interesting across countries, keep
per-period dispatch for a sampled subset of days rather than reverting the decision
wholesale.

## Guardrails

- Index `(country, datetime)` on every fact table.
- Partition by country or year if any table passes ~50M rows.
- Prune old runs. `model_run` records commit, config and seed precisely so a run is
  reproducible; keeping every historical run forever was never the intent.

Expected end state with these in place: **1 to 1.5 GB**, roughly double today, with query
times unchanged. Without them: ~7 GB and slow joins, and the whole difference is the
dispatch decision.
