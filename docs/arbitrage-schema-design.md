# Arbitrage schema — design for review

The design for the five arbitrage tables. `CLAUDE.md` reserves schema design as the
user's call, so this was reviewed before any DDL was written; the outcome is recorded in
"Decisions taken" at the end. The tables themselves land in a later migration.

## The problem it has to solve

The standing convention is *don't store derived data*: anything computable at query time
stays a query-time computation. Forecasts and dispatch schedules look like they violate
that, and the resolution decides the shape of all five tables.

The exemption holds, but for two different reasons depending on the strategy, and they
are worth keeping apart rather than waving at both at once.

**Reason one: some runs cannot be recomputed at all.** The LSTM forecaster and the RL
agent each depend on three things that do not live in the database:

- **Weights** — the learned parameters of a trained model, sitting in a model file. Once
  trained, the model's output is entirely determined by those numbers.
- **Seed** — the starting value of the random number generator. Training is stochastic
  in several places (weight initialisation, batch shuffling, dropout), so the same code
  on the same data with a different seed produces a different model.
- **Horizon** — how far ahead the controller looks. A full battery at 17:00 discharges
  into tonight's peak on a four-hour horizon and holds for tomorrow morning on a
  thirty-six-hour one. Same data, same weights, a completely different schedule.

No query can reproduce output that depends on state the database never held.

**Reason two: some runs could be recomputed, but must not be.** The perfect-foresight LP
and the naive heuristic are fully deterministic: given the price series they reproduce
exactly. Storing them is a cost decision rather than a correctness one, because
re-solving an optimisation across ~300,000 settlement periods every time someone draws a
chart is not a query-time computation in any useful sense.

| Strategy | Weights | Seed | Horizon | Recomputable? | Why stored |
| --- | --- | --- | --- | --- | --- |
| `lp_perfect_foresight` | none | none | window | yes | cost |
| `naive_tod` | none | none | n/a | yes | cost |
| `lstm_mpc` | yes | yes | yes | no | not reproducible |
| `rl_dqn` | yes | yes | yes | no | not reproducible |

Either way they are *observations of a run*, and a run is a fact like any other. The rule
that falls out: **store what a run did, compute what it earned.** Profit never enters the
database, because it is a join of `dispatch` against `price` and is exactly the kind of
thing the convention forbids storing.

Note that `seed` is nullable in `model_run` precisely because the top two rows of that
table have none. A NULL seed is a positive statement that the run was deterministic, not
a missing value.

## The five tables

### `battery_spec` — dimension
The physical asset being simulated. Hand-curated assumptions, so it sits alongside `fuel`
as a modelling layer rather than an observed fact.

| Column | Type | Notes |
| --- | --- | --- |
| `battery_id` | serial PK | |
| `name` | text, unique | e.g. `'2h_50mw'` |
| `capacity_mwh` | double, > 0 | usable energy |
| `power_mw` | double, > 0 | charge/discharge rate limit |
| `round_trip_efficiency` | double, 0–1 | one-way taken as its square root, by convention |
| `min_soc_mwh` | double, default 0 | floor, for degradation headroom |
| `max_cycles_per_day` | double, nullable | NULL means unconstrained |

### `strategy` — dimension
One row per implementation: `lp_perfect_foresight`, `naive_tod`, `lstm_mpc`, `rl_dqn`.

### `model_run` — dimension
The reproducibility record. A dispatch schedule is meaningless without the code, config
and seed that produced it.

| Column | Type | Notes |
| --- | --- | --- |
| `run_id` | serial PK | |
| `strategy_id`, `battery_id` | FK | |
| `created_at` | timestamptz | |
| `git_commit` | text | the commit the run executed at |
| `config` | jsonb | hyperparameters, horizon, solver settings |
| `seed` | int, nullable | NULL for deterministic strategies (LP, heuristic) |
| `period_start`, `period_end` | timestamptz | the backtest window |
| `solver_status` | text, nullable | optimal / infeasible / time-limit |

`solver_status` earns its place because it is genuinely an observation of the run and is
not cheaply recomputable: it records whether the LP actually reached optimality.

### `dispatch` — fact
One row per (run, settlement period).

| Column | Type | Notes |
| --- | --- | --- |
| `run_id` | FK, on delete cascade | |
| `time_id` | FK | |
| `charge_mw` | double, >= 0 | |
| `discharge_mw` | double, >= 0 | |
| `soc_mwh` | double, >= 0 | state of charge at period end |

PK `(run_id, time_id)`, plus an index on `time_id` for cross-run comparison at a period.

Charge and discharge are separate columns rather than one signed `net_mw`, and `soc_mwh`
is stored rather than reconstructed. Both were contested; the reasoning that settled them
is in "Decisions taken" below. Two CHECK constraints follow from those choices:
`CHECK (charge_mw = 0 OR discharge_mw = 0)` and
`CHECK (soc_mwh BETWEEN min_soc_mwh AND capacity_mwh)`.

### `forecast` — fact
One row per (run, forecast origin, horizon step).

| Column | Type | Notes |
| --- | --- | --- |
| `run_id` | FK, on delete cascade | |
| `origin_time_id` | FK | when the forecast was made |
| `horizon_step` | smallint, > 0 | 1 = next settlement period |
| `target_time_id` | FK | the period being predicted |
| `predicted_price` | double | |

**This is a refinement on the approved plan**, which specified `(run_id, time_id,
horizon_step)`. A receding-horizon controller makes a fresh forecast at every step, so a
prediction has *two* timestamps: when it was made and what it is about. Collapsing them
loses the ability to ask how forecast error grows with horizon, which is the main thing
worth knowing about the forecaster.

## What stays out

- **Profit and revenue.** A join of `dispatch` to `price`.
- **Percentage of optimum.** A join of one run against the `lp_perfect_foresight` run over
  the same window and battery. This is analysis SQL, so under the coaching boundary it is
  yours to write.
- **Cycle counts, utilisation, spread capture.** All aggregations over `dispatch`.

## Decisions taken

Confirmed 2026-09-02.

1. **`time` is renamed to `settlement_period`.** Applied in the baseline migration
   `ed7e02dcf29d`. Beyond avoiding a Postgres type name, the new name says what the row
   actually is: a half-hour GB settlement period, not a generic instant.

2. **Separate `charge_mw` and `discharge_mw`**, not one signed column. The deciding
   argument is error detection, not storage. Simultaneous charge and discharge is a real
   LP failure mode: it appears when efficiency is mis-specified, and during negative
   price periods where the optimiser discovers it can profitably burn energy by cycling
   it in and out at once. A signed column cannot represent that state, so the bug is
   silently netted away and never surfaces. Separate columns plus
   `CHECK (charge_mw = 0 OR discharge_mw = 0)` turn the database into a detector for it.

3. **`soc_mwh` is stored, with a bounds CHECK.** The no-derived-data rule exists to stop
   stored derivations drifting out of sync when base data changes, and `schema.sql`
   already sanctions the calendar dimension on exactly that reasoning: "a calendar is
   immutable: no update-anomaly risk". Model runs are append-only, so the anomaly the
   rule guards against cannot occur here either. Storing it also preserves the solver's
   own arithmetic rather than a reconstruction that drifts across 300k cumulative steps,
   and it enables `CHECK (soc_mwh BETWEEN min_soc_mwh AND capacity_mwh)` as a genuine
   test that the optimiser respected its own constraints.

4. **Battery parameters: still open.** Does not block the migration, only the first
   backtest run.
