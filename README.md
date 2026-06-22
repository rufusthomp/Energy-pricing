# GB Electricity Merit-Order Analyser

A SQLite data product that reconstructs the GB electricity **supply (merit-order) stack** from
half-hourly generation, demand, and wholesale-price data, and identifies the **price-setting
(marginal) technology** over time, then compares a modelled marginal price against the actual
market price.

In a power market, generators are dispatched cheapest-first until supply meets demand. The
**last (most expensive) unit needed sets the wholesale price** ([merit order & marginal
pricing](https://www.sqe.energy/insights/understanding-power-markets-merit-order-and-marginal-pricing)).
Reconstructing that stack is naturally a *cumulative-sum-until-demand-is-met* problem, which makes
it a clean showcase for SQL window functions.

## Key results

Reconstructed from ~3.4M half-hourly generation records (2009–2026):

- **Gas sets the price ~71% of the time** (it is the marginal technology in 95k of 134k settlement
  periods with price data), with the marginal fuel sliding *down* the stack overnight (imports,
  biomass) as demand falls.
- **The decarbonisation transition, straight from the data:** coal's average output collapses from
  **11.3 GW (2009) to 0 (2025)**, while wind (incl. embedded) grows roughly **24×**; biomass appears
  in 2017 (Drax conversion) and solar from 2013.
- **Modelled vs actual price exposes when a static-cost model breaks:** the modelled marginal price
  tracks the actual Market Index Price reasonably in stable years, but diverges by **+£123/MWh in
  2022** (actual avg £197 vs modelled £74) during the gas crisis, because a fixed gas cost cannot
  represent a 5–10× gas-price spike. This motivates the time-varying SRMC extension (see Future work).

## Repository structure

```
gb-merit-order/
├── README.md
├── schema.sql            # CREATE TABLEs + indexes — source of truth for the DB
├── sql/queries.sql       # analysis queries (merit order, generation mix, modelled vs actual)
├── src/load.py           # Python ETL: download/read, transform, load into SQLite
├── notebooks/explore.ipynb  # exploratory prototyping of the transforms
├── data/raw/             # source CSVs + cached price pull (gitignored)
└── requirements.txt
```

The compiled `.db` is **not** version-controlled. The SQL recipe is. Running `load.py` regenerates
the database from `schema.sql` plus the source data, so the database is disposable and reproducible.

## Data sources

| Domain | Source | Notes |
|--------|--------|-------|
| Generation | [NESO Historic Generation Mix](https://www.neso.energy/data-portal/historic-generation-mix) (`df_fuel_ckan.csv`) | Half-hourly MW by fuel, 2009–present. Loaded wide, normalised to long. |
| Demand | [NESO Historic Demand Data](https://www.neso.energy/data-portal/historic-demand-data) (per-year CSVs) | National Demand (ND) and Transmission System Demand (TSD); both stored. |
| Price | [Elexon Insights API](https://developer.data.elexon.co.uk/) — Market Index Price (MID) | 2018–present; fetched in 7-day windows (API cap), volume-weighted across providers. |

## Schema design

A **star schema**: two dimension tables (`fuel`, `time`) and three fact tables (`generation`,
`demand`, `price`).

**Normalisation: wide → long.** The generation CSV is wide (one column per fuel). It is unpivoted
into a long `generation` fact table (`time_id`, `fuel_id`, `mw`) so a fuel is a *row*, not a
*column*; this is what lets the merit order be computed with `ORDER BY mc` + a cumulative window
function. Derived columns from the source (`_perc`, aggregates like `GENERATION`) are **dropped and
recomputed in SQL** rather than stored, to avoid update anomalies (don't store derived data).

**`time` dimension with a surrogate `time_id`.** Facts reference an integer `time_id` rather than a
text timestamp, because integer joins are cheaper than matching on strings, and the time table can
define custom calendar attributes (e.g. `season`) *once* for consistency across queries. This is
traded off against an extra join in most queries. The derived calendar columns (`date`, `month`,
`year`, `season`) are stored despite the don't-store-derived rule because a calendar is immutable
reference data and so cannot suffer update anomalies.

**Keys, constraints, and an index.**
- `generation` uses a **composite primary key `(time_id, fuel_id)`**, which captures its grain
  (one measurement per fuel per period) and blocks duplicate rows for free.
- An extra index on `generation(fuel_id)` supports fuel-only aggregations (the composite PK's
  leftmost column is `time_id`, so a fuel-only filter is not covered by it).
- `fuel.name` and `time.datetime` are `UNIQUE`; `demand`/`price` are keyed by `time_id`.

**`fuel` as a modelling layer.** The `fuel` dimension is hand-curated reference data: each fuel's
short-run marginal cost (`mc`, £/MWh), carbon factor, and a dispatchable flag. The `mc` column is a
deliberate modelling assumption (the merit order), kept separate from the observed facts.

## ETL pipeline

`src/load.py` builds the whole database in one run:

1. Execute `schema.sql` (`DROP`/`CREATE`, fully re-runnable).
2. Insert the hand-curated `fuel` reference rows (parameterised `executemany`).
3. Build the `time` dimension from the distinct timestamps (deriving date/month/year/season).
4. Unpivot the generation CSV (`pandas.melt`), map fuel names and timestamps to surrogate keys, and
   bulk-load `generation`.
5. Concatenate the per-year demand CSVs, reconstruct each timestamp from settlement date + period,
   and load `nd`/`tsd`.
6. Read the cached MID pull, volume-weight the two providers into one price per period, and load
   `price`.

Run it from `src/`:

```bash
pip install -r requirements.txt
python load.py
```

> Settlement periods: each day is split into half-hourly **settlement periods** (1 = 00:00–00:30,
> ..., 48 = 23:30–24:00). Demand is keyed by date + period, so the datetime is reconstructed as
> `date + (period - 1) * 30 minutes`.

## Analysis queries (`sql/queries.sql`)

- **Merit order / marginal fuel** — a multi-table join feeding a cumulative `SUM(mw) OVER
  (PARTITION BY time_id ORDER BY mc)`, wrapped in CTEs with `ROW_NUMBER()` to pull, for every
  period, the cheapest fuel whose cumulative supply meets demand: the price-setting technology.
- **Generation mix by year** — a `GROUP BY year, fuel` aggregation showing the fuel mix evolving.
- **Modelled vs actual price** — joins the modelled marginal cost to the actual MID and computes
  the gap.

## Modelling assumptions & limitations

- **Static marginal costs.** `mc` is a single fixed value per fuel. Real short-run marginal cost
  (especially gas and coal) varies with fuel and carbon prices; this is the model's main limitation
  and the source of the 2022 divergence above.
- **Demand basis.** Both ND and TSD are stored; the merit-order crossover uses TSD (it better
  reflects the total generation the stack must serve, so it is more appropriate for pricing).
- **Biomass carbon factor = 0** (the ETS treatment that drives its dispatch economics), even though
  its physical stack emissions are coal-like and its carbon-neutrality is contested.
- **MID coverage** begins ~2018, so the price comparison is limited to 2018 onward; generation and
  demand cover the full 2009–2026 span.
- Clock-change days produce a small number of duplicate timestamps, which are de-duplicated on load.

## Future work

- **Time-varying SRMC (v2):** drive gas/coal marginal cost from historical gas and carbon prices
  (with the UK Carbon Price Support and the EUA→UKA transition), computed at query time from a new
  commodity-price table. Expected to close most of the 2021–22 divergence.
- **Dunkelflaute analysis:** identify periods of simultaneously low wind and solar output.
- **Generation-mix percentage shares** via a windowed denominator.

## Tech stack

Python (pandas, requests), SQLite, DB Browser for SQLite, Jupyter.
