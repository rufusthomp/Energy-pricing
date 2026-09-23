# Where the project is

Last updated 2026-09-23. **Read this first.** Then, depending on the task:

| If you are about to... | Read |
| --- | --- |
| Query or change the database | `schema.md`, then `conventions.md` |
| Run any analysis on the European panel | `research-design.md` |
| Choose or change the research question | `research-questions.md` |
| Touch the GB battery study or its results | `findings.md` |
| Change what gets stored, or at what grain | `data-scaling.md` |

This file holds only the current state and what comes next. Design arguments live in the
documents above; history lives in git and in migration docstrings.

## What this is

1. **A GB merit-order model** (v1 static cost, v2 dynamic SRMC). Explains annual GB
   wholesale price levels to within about £8/MWh. Complete; now mainly a data source.
2. **A GB battery arbitrage study.** A perfect-foresight MILP ceiling, a clock-rule floor,
   and a gradient-boosted forecaster in between. Complete, with results in `findings.md`.
3. **A European panel paper, in progress.** 21 bidding zones from ENTSO-E, used to
   identify what GB alone cannot: whether renewables change *who* captures storage value.

## State at a glance

| Piece | State |
| --- | --- |
| Package, Postgres 17, Alembic, pytest, CI | done; 101 tests, CI green |
| Database | four schemas (`ref`, `gb`, `entsoe`, `model`), one time key; see `schema.md` |
| GB data, MILP, heuristic, forecaster, backtests | done; 6 runs stored in `model.run` |
| ENTSO-E panel | pulled and loaded 2026-09-23: 21 zones, 2018 to 2026-09-21, 7.68M rows |
| Research question | **not yet chosen**; candidates in `research-questions.md` |
| Panel backtests | **not started**; `backtest.py` is GB-only |

## Next steps, in order

1. **The user chooses the primary question.** The recommendation in
   `research-questions.md` is a chain (price shape → information → forecast quality), plus
   the Iberian exception as a short standalone paper. Record the choice, and its single
   primary outcome, in `research-design.md` *before* running any regression. With many
   candidate outcomes, choosing after seeing results is how the two retracted claims below
   happened.
2. **Build the capacity proxy.** Reported capacity is too sparse (see below). Use the
   annual 99th percentile of hourly wind plus solar from `entsoe.generation`. It is a
   modelling choice, so make it a query or view, not a stored table.
3. **Generalise the backtest harness to the panel.** It should read `entsoe.price` by zone,
   optimise over `entsoe.calendar.delivery_date` (the auction's CET day, **not** the local
   date), write `model.daily_result` with `price_source = 'entsoe_day_ahead'`, and not
   write per-period dispatch. `gbmo.arbitrage.lp` and `heuristic` know nothing about
   zones, but both assume GB's grain: `PERIOD_HOURS = 0.5` is a module constant, and the
   heuristic's windows (`range(8)`, `range(32, 40)`) are half-hour indices on a UTC day.
   Panel hours are 1.0, and a clock rule has to run on local hours
   (`entsoe.calendar.local_hour`), or "charge overnight" means a different time of day in
   every zone. Make both parameters, and check the GB results still reproduce exactly.
   Note that the auction's delivery day has 23 or 25 hours on clock-change days.
4. **Run the GB cross-check.** Run the ceiling on ENTSO-E GB (2019–20) and compare it with
   the Elexon-based runs. This validates both pipelines at once. The two are different
   products, an auction against a within-day index, so expect high correlation rather than
   equality.
5. **Then the chosen analysis**, following `research-design.md`.

## The panel: what it actually contains

Coverage is the share of expected hours present, with absent years counted as zero.

- **19 zones are complete:** 98–100% on price, load, generation and both forecasts,
  2019–2026.
- **GB is not a panel zone.** ENTSO-E prices stop on 2020-12-31, and the rest stops in
  mid-2021. It is kept for the cross-check only.
- **IE_SEM is price-complete but forecast-poor.** Its load forecast is 1–4% present after
  mid-2021. Drop it from anything that needs the forecast information set.
- **Reported capacity is clean for only 16 zones.** IT_NORD has none, SE_3 and SE_4 have
  one year each, and CH has no wind or solar line.
- **Resolution:** about a third of 2025–26 zone-years were published at 15 minutes. All
  are resampled to hourly on load, and `entsoe.ingest` records the native resolution.
- **Currency:** every panel price is EUR (Poland included), confirmed against the
  platform's raw XML with `python -m gbmo.ingest.entsoe --verify`.

**If you re-pull from ENTSO-E:** the token is in the gitignored `.env`. Each request costs
about 10 seconds regardless of size, and generation is the slowest dataset at 1–2 minutes
per zone-year. The platform drops the connection, rather than returning 429, above 400
requests a minute and bans the token for about ten minutes. Parallel workers by dataset
are safe: three workers make about 12 requests a minute. Give the workers different zone
orders, or they fetch the same files in lockstep. The cache is resumable, so only missing
files are fetched.

## GB study: headline results

50 MW battery, 2018 to mid-2026, capture as a share of the perfect-foresight ceiling:

| Battery | Clock rule | Forecast | + Weather | Oracle forecast |
| --- | --- | --- | --- | --- |
| 1h | 24.3% | 42.7% | 48.0% | 54.4% |
| 4h | 51.7% | 54.8% | 62.7% | 69.0% |

The short-run finding holds up: on renewable-heavy days, forecasting is worth more,
robust to year-by-month fixed effects. The structural version (does long-run
decarbonisation transfer value?) is **not identifiable from GB alone**, and that is why
the panel exists.

## Two retracted claims: read before running any regression

Both are documented in `findings.md` rather than deleted.

- **"Capture rate is decaying"** (section 5.3). Asserted from two endpoints of a noisy
  eight-point series; t between −1.37 and −2.13 on six degrees of freedom.
- **"Decarbonisation transfers storage value to sophisticated operators"** (section 5.6).
  Month fixed effects only. Dropping the gas crisis took the coefficient from +0.0075 to
  +0.0001, and adding year fixed effects flipped it negative and significant.

**The lesson:** with a monotonically trending regressor, a specification without time
fixed effects will report a strong, significant association between any two series that
both happen to rise. Always run the version with time effects before believing anything.

## Dead ends: do not retry without new information

- **Structural counterfactual via the merit-order model.** Its intraday shape correlates
  with actual prices at only r = 0.35, even with gas efficiency rungs. The binding
  constraint is structural: unit commitment, scarcity rents and must-run negative pricing
  are not marginal-cost phenomena.
- **Reduced-form counterfactual.** Retained in `findings.md` section 5.10 as illustration
  only. Model-generated prices lack the variation the model cannot explain, so a
  forecaster scores 77–86% on them against 50.5% on real prices.
- **A monthly panel with month fixed effects only.** See the retractions above.

## Open issue: the marginal-fuel tie in `sql/queries.sql`

Queries 1, 2 and 4 pick the marginal fuel with `ROW_NUMBER() OVER (PARTITION BY datetime
ORDER BY mc)`. WIND, WIND_EMB and SOLAR all have `mc = 0`, so when they tie, Postgres names
whichever it reaches first, and that can change **between runs on identical data**. It
affects about 0.4% of periods in the v1 stack and 0.1% in v2. **No price, cost or
cumulative-supply figure is affected** (maximum deviation exactly 0.0); only the fuel
*name* moves.

The fix is the user's call, because the file is theirs and the choice is a modelling one:
either a tie-breaker (`ORDER BY mc, fuel_id`, deterministic but arbitrary), or reporting
"zero-cost renewable" as a category. The second is arguably more honest, since none of
the three is uniquely marginal.

## Other open questions, none needing a trend

- What is a weather feed worth in £/MW/year? The ablation gives it directly.
- What is the elasticity of revenue to forecast error, in £ lost per £1/MWh of MAE?
- Why is forecasting worth 18 points at one hour but only 3 at four hours?
- How much of the ceiling is structurally unreachable? Even the oracle stops at 69%.
- An LSTM compared against the gradient-boosted baseline, which trains in 13 seconds.

## Running it

```bash
pip install -e ".[dev]"
docker compose up -d
python -m alembic upgrade head
python -m gbmo.ingest.weather          # weather cache, once
python -m gbmo.ingest.load             # gb schema from data/raw/, about 5 min
python -m gbmo.ingest.entsoe --verify  # needs GBMO_ENTSOE_TOKEN in .env
python -m gbmo.ingest.entsoe           # ENTSO-E cache, hours, resumable, once
python -m gbmo.ingest.load_zones       # entsoe schema from the cache, about 2 min
python -m gbmo.arbitrage.backtest --strategy all   # GB backtests, about 2 min
pytest -q && ruff check src tests
```

Raw inputs are gitignored, so a fresh clone needs the sources listed in the README before
anything will run. The two loaders are independent, and neither touches `model`, so
backtest runs survive both.
