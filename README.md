# GB Electricity Merit-Order Analyser

A SQLite data product that reconstructs the GB electricity **supply (merit-order) stack** from
half-hourly generation, demand, and wholesale-price data, and identifies the **price-setting
(marginal) technology** over time, then compares a modelled marginal price against the actual
market price.

In a power market, generators are dispatched cheapest-first until supply meets demand. The
**last (most expensive) unit needed sets the wholesale price** ([merit order & marginal
pricing](https://www.sqe.energy/insights/understanding-power-markets-merit-order-and-marginal-pricing)).
Reconstructing that stack is naturally a *cumulative-sum-until-demand-is-met* problem, which makes
for a nice demonstration of SQL window functions.

## Key results

Reconstructed from ~3.4M half-hourly generation records (2009–2026):

- **Gas sets the price ~65% of the time** under the time-varying model (71% under the static one),
  with the marginal fuel sliding *down* the stack overnight (imports, biomass) as demand falls.
- **The decarbonisation transition, straight from the data:** coal's average output falls dramatically from
  **11.3 GW (2009) to 0 (2025)**, while wind (incl. embedded) grows roughly **24×**; biomass appears
  in 2017 (Drax conversion) and solar from 2013.
- **A static-cost model breaks in *both* directions.** A fixed gas cost of £70 **over-prices by
  ~£27–40/MWh** in the cheap-gas years (2018–20) and **under-prices by £123/MWh in 2022** (actual avg
  £197 vs modelled £74). One cause: a fixed cost cannot track the real gas price.
- **Time-varying SRMC closes most of that gap — and exposes a second, larger effect.** Pricing gas and
  coal from monthly fuel and carbon prices cuts the mean absolute annual error from **£37.3 to
  £19.2/MWh**. Switching the gas input from the *contract* price generators paid (DESNZ QEP) to the GB
  *spot* price (ONS SAP) cuts it again to **£7.8/MWh** — 2021 lands within £0.80 and 2025 within £1.20.
  Which gas price represents the marginal generator's opportunity cost turns out to matter **more than
  making the cost time-varying at all**. QEP is contract-weighted and lags: in 2023 it left the model
  over-pricing by £61/MWh, worse than the static model, while spot gas priced the same year to £4.
- **The coal→gas flip falls out of the prices rather than being assumed.** Coal's SRMC runs £30/MWh
  against gas at £55 in early 2013, and £56 against gas at £35 by April 2020. The static model could
  not represent that crossover at all: it hardcoded coal (£110) above gas (£70) in every period of all
  17 years, which made coal look price-setting **36%** of the time against **8%** under v2.

## Repository structure

```
gb-merit-order/
├── README.md
├── pyproject.toml        # package metadata + pinned dependencies (single source of truth)
├── schema.sql            # CREATE TABLEs + indexes — source of truth for the DB
├── sql/queries.sql       # analysis queries (merit order, generation mix, modelled vs actual)
├── src/gbmo/
│   ├── config.py         # paths, resolved from the package, not the working directory
│   └── ingest/
│       ├── load.py       # ETL orchestration: rebuilds every table in one run
│       ├── transform.py  # pure transforms (grain conversion, CPS schedule, price collapse)
│       ├── reference.py  # the hand-curated fuel modelling layer
│       └── sources.py    # sources + cleans the commodity inputs (coal from QEP, ECB FX)
├── tests/                # unit tests over the transforms
├── notebooks/explore.ipynb  # exploratory prototyping of the transforms
└── data/raw/             # source CSVs + cached price pull (gitignored)
```

## Running it

```bash
pip install -e ".[dev]"        # installs the package and its pinned dependencies
python -m gbmo.ingest.load     # rebuild data/gb-merit-order.db from data/raw/
pytest -q                      # unit tests
ruff check src tests           # lint
```

The build is disposable and reproducible: `schema.sql` drops and recreates every table,
so re-running is always safe and never leaves a half-loaded database. Raw inputs are
gitignored, so a fresh clone needs the sources listed below before the ETL will run.

`python -m gbmo.ingest.load --db PATH` builds to an alternative file, which is how a
change to the ETL is checked for equivalence against a known-good database.

## Data sources

| Domain | Source | Notes |
|--------|--------|-------|
| Generation | [NESO Historic Generation Mix](https://www.neso.energy/data-portal/historic-generation-mix) (`df_fuel_ckan.csv`) | Half-hourly MW by fuel, 2009–present. Loaded wide, normalised to long. |
| Demand | [NESO Historic Demand Data](https://www.neso.energy/data-portal/historic-demand-data) (per-year CSVs) | National Demand (ND) and Transmission System Demand (TSD). |
| Price | [Elexon Insights API](https://developer.data.elexon.co.uk/) — Market Index Price (MID) | 2018–present; fetched in 7-day windows (API cap), volume-weighted across providers. |
| Gas & coal | [DESNZ Quarterly Energy Prices 3.2.1](https://www.gov.uk/government/statistical-data-sets/prices-of-fuels-purchased-by-major-power-producers) | Quarterly p/kWh (GCV) paid by major power producers, excl. CPS. Monthly GB spot gas (ONS SAP) loaded alongside as an alternative. |
| Carbon | [ICAP Allowance Price Explorer](https://icapcarbonaction.com/en/ets-prices) | Daily EUA (EUR) and UKA (GBP) secondary-market prices, plus the statutory CPS schedule. |
| FX | [ECB reference rates](https://api.frankfurter.dev) | EUR→GBP, to price the EUA series in sterling. |

Full provenance, units, coverage and caveats for the commodity series: [`data/raw/commodity/SOURCES.md`](data/raw/commodity/SOURCES.md).

## Schema design

A **star schema**: dimensions `fuel` and `time`, facts `generation`, `demand`, `price`. Key choices:

- **Wide → long.** The generation CSV (one column per fuel) is unpivoted into
  `generation(time_id, fuel_id, mw)`, so a fuel is a *row*, not a column: this is what lets the merit
  order be an `ORDER BY mc` + cumulative window function. Source-derived columns (`_perc`, totals)
  are dropped and recomputed in SQL rather than stored.
- **Surrogate `time_id`.** Facts join on an integer `time_id` (cheaper than string-timestamp joins),
  and the `time` table defines calendar attributes like `season` once. Its derived columns are stored
  because a calendar is immutable (no update-anomaly risk).
- **Keys & index.** `generation` has a composite PK `(time_id, fuel_id)` (its grain; blocks
  duplicates), plus an index on `fuel_id` for fuel-only aggregations; `demand`/`price` are keyed by
  `time_id`.
- **`fuel` as a modelling layer.** Hand-curated reference data (`mc`, carbon factor, efficiency,
  dispatchable flag); these are modelling assumptions, kept separate from the observed facts.
  `efficiency` and `carbon_factor` are *not* independent — the chemistry fixes emissions per MWh of
  heat (gas 202, coal 341 kgCO₂/MWh_th, LHV), so `carbon_factor = heat_emissions / efficiency`.
  `fuel.commodity` names the price series that drives a fuel's SRMC, or is `NULL` for fuels priced
  by the static `mc`.
- **`commodity_price` stores series, not conclusions.** Each series is loaded as observed and keyed
  `(year, month, commodity, source)`. The EUA→UKA splice date, whether CPS is added, and QEP vs SAP
  for gas are all *modelling choices*, so they are made in the query rather than baked into the
  data — which is what `source` exists to make possible. Units vary by commodity, hence the `unit`
  column: never compare across commodities without reading it.

## ETL pipeline

`src/load.py` rebuilds the database in one run: execute `schema.sql`, insert the hand-curated `fuel`
rows, then load each fact table. The generation CSV is unpivoted (`pandas.melt`), the per-year demand
CSVs are concatenated, and the cached MID pull is collapsed (volume-weighted across providers) into
one price per period; foreign keys are resolved by mapping names/timestamps to surrogate keys.

```bash
pip install -r requirements.txt
python fetch_commodity.py   # run from src/ — only needed to refresh the commodity CSVs
python load.py              # run from src/
```

> Settlement periods: each day has 48 half-hourly periods; demand is keyed by date + period, so the
> timestamp is rebuilt as `date + (period − 1) × 30 min`.

## Analysis queries (`sql/queries.sql`)

- **Merit order / marginal fuel** — a multi-table join feeding a cumulative `SUM(mw) OVER
  (PARTITION BY time_id ORDER BY mc)`, wrapped in CTEs with `ROW_NUMBER()` to pull, for every
  period, the cheapest fuel whose cumulative supply meets demand: the price-setting technology.
- **Generation mix by year** — a `GROUP BY year, fuel` aggregation showing the fuel mix evolving.
- **Modelled vs actual price** — joins the modelled marginal cost to the actual MID and computes
  the gap.
- **Dynamic SRMC merit order (v2)** — the same cumulative-window pattern, but ordered on an SRMC
  computed per `(fuel, month)` from `commodity_price` rather than on the fixed `fuel.mc`. Three CTEs
  build it: `carbon` collapses the EUA/UKA/CPS rows into one effective carbon price per month (the
  `COALESCE` lands the EUA→UKA splice on the right month with no hardcoded date, since UKA only
  exists from 2021-05); `month_fuel` cross-joins the calendar to `fuel` so every fuel is priced in
  every month; `srmc` applies the cost formula with a fallback to `fuel.mc`.
- **v1 vs v2 by year** — runs both stacks and joins them on `time_id`, so the two models are compared
  over identical settlement periods even where they disagree about which fuel is marginal.

> Two traps worth knowing if you edit these. **Pin `source` in the commodity join** — `commodity =
> 'gas'` matches both the QEP and SAP rows, and an unpinned join puts gas in the stack twice, silently
> double-counting its capacity in the cumulative sum. And **both window functions must order on the
> same key**: the cumulative `SUM` defines dispatch order and the `ROW_NUMBER` picks the cheapest
> qualifying rung, so if they disagree the marginal fuel is wrong without anything erroring.

## Modelling assumptions & limitations

- **Two costing models, both retained.** v1 prices every fuel at a fixed `fuel.mc`; v2 computes SRMC
  per month from fuel and carbon prices. v1 is kept as the baseline the v2 error is measured against,
  not because it is defensible.
- **v2 falls back to the static `mc` wherever an input is missing**, which is deliberate but means the
  model is not dynamic everywhere. Three cases: the eight fuels with no commodity series behind them
  (hydro, nuclear, biomass, imports, storage, other, and the two wind rows); the **2023 Q3 coal price**,
  which DESNZ suppressed mid-series; and **every month after 2026-03**, where the carbon series ends —
  which is **47% of 2026**, so that year's £-14.6/MWh error is not a clean read on v2.
- **Monthly commodity grain against half-hourly dispatch.** SRMC steps once a month, so it cannot
  capture within-month gas moves or the intraday spread. This is the largest remaining source of error
  in the v2 residuals.
- **Efficiency is a single fleet-average number per fuel** (gas 0.50, coal 0.36, LHV), not a per-unit
  or time-varying figure, so the real fleet's spread of efficiencies is compressed to a point. Because
  `carbon_factor = heat_emissions / efficiency`, changing one without the other breaks consistency.
- **QEP vs SAP measure different things.** QEP is the price generators *paid* (contract-weighted, lags
  the market); SAP is GB spot. The model prefers SAP where it exists (2018+) and falls back to QEP
  before that, so the pre-2018 modelled prices are on the laggier basis and should be read as such.
- **Demand basis.** Both ND and TSD are stored; the merit-order crossover uses TSD (it better
  reflects the total generation the stack must serve, so it is more appropriate for pricing).
- **Biomass carbon factor = 0** (the ETS treatment that drives its dispatch economics), even though
  its physical stack emissions are coal-like and its carbon-neutrality is contested.
- **MID coverage** begins ~2018, so the price comparison is limited to 2018 onward; generation and
  demand cover the full 2009–2026 span.
- Clock-change days produce a small number of duplicate timestamps, which are de-duplicated on load.

## Future work

- **Daily or half-hourly commodity grain.** The monthly step is now the dominant residual error. The
  ONS SAP daily gas series and the ICAP daily allowance series are both already downloaded, so this is
  a regrind of the ETL rather than new sourcing.
- **Extend the modelled span past 2026-03,** where the carbon series ends and v2 silently reverts to
  static costs for 47% of 2026.
- **Per-unit rather than fleet-average efficiency,** so the stack has a spread of gas rungs instead of
  a single one — which is what would let the model reproduce the intraday spread.
- **Dunkelflaute analysis:** identify periods of simultaneously low wind and solar output.
- **Generation-mix percentage shares** via a windowed denominator.

## Tech stack

Python (pandas, requests), SQLite, DB Browser for SQLite, Jupyter.
pytest and ruff, run on Python 3.11 and 3.13 in GitHub Actions.
