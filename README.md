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

- **Gas sets the price ~71% of the time** (it is the marginal technology in 95k of 134k settlement
  periods with price data), with the marginal fuel sliding *down* the stack overnight (imports,
  biomass) as demand falls.
- **The decarbonisation transition, straight from the data:** coal's average output falls dramatically from
  **11.3 GW (2009) to 0 (2025)**, while wind (incl. embedded) grows roughly **24×**; biomass appears
  in 2017 (Drax conversion) and solar from 2013.
- **Modelled vs actual price exposes how a static-cost model breaks:** the modelled marginal price
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

## Data sources

| Domain | Source | Notes |
|--------|--------|-------|
| Generation | [NESO Historic Generation Mix](https://www.neso.energy/data-portal/historic-generation-mix) (`df_fuel_ckan.csv`) | Half-hourly MW by fuel, 2009–present. Loaded wide, normalised to long. |
| Demand | [NESO Historic Demand Data](https://www.neso.energy/data-portal/historic-demand-data) (per-year CSVs) | National Demand (ND) and Transmission System Demand (TSD). |
| Price | [Elexon Insights API](https://developer.data.elexon.co.uk/) — Market Index Price (MID) | 2018–present; fetched in 7-day windows (API cap), volume-weighted across providers. |

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
- **`fuel` as a modelling layer.** Hand-curated reference data (`mc`, carbon factor, dispatchable
  flag); `mc` is the modelling assumption, kept separate from the observed facts.

## ETL pipeline

`src/load.py` rebuilds the database in one run: execute `schema.sql`, insert the hand-curated `fuel`
rows, then load each fact table. The generation CSV is unpivoted (`pandas.melt`), the per-year demand
CSVs are concatenated, and the cached MID pull is collapsed (volume-weighted across providers) into
one price per period; foreign keys are resolved by mapping names/timestamps to surrogate keys.

```bash
pip install -r requirements.txt
python load.py   # run from src/
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
