"""Invariants a dispatch schedule must satisfy, that a CHECK constraint cannot express.

Postgres CHECK constraints see only the row they are attached to, so the constraints in
migration f75c7e384d2f cover the same-row conditions and no more: flows non-negative,
state of charge non-negative, and never charging and discharging in the same period.

The physical limits are all cross-table. Whether a state of charge exceeds capacity, or
a flow exceeds the power rating, depends on `battery_spec` via `model_run`, which a CHECK
cannot reach. A trigger could, at the cost of firing per row on a bulk insert of a
300k-row backtest.

So they are enforced here instead, as a query run after a backtest writes. That is a
weaker guarantee than a constraint, because it catches a violation after the fact rather
than preventing it, and it has to be called. It is recorded rather than hidden: the
backtest harness calls this before committing a run as complete.
"""

from sqlalchemy import text

# Each returns rows only when the invariant is broken, so an empty result is a pass.
INVARIANTS = {
    "soc_above_capacity": """
        SELECT d.run_id, count(*) AS violations, max(d.soc_mwh - b.capacity_mwh) AS worst
        FROM dispatch d
        JOIN model_run r ON r.run_id = d.run_id
        JOIN battery_spec b ON b.battery_id = r.battery_id
        WHERE d.soc_mwh > b.capacity_mwh + 1e-6
        GROUP BY d.run_id
    """,
    "soc_below_floor": """
        SELECT d.run_id, count(*) AS violations, max(b.min_soc_mwh - d.soc_mwh) AS worst
        FROM dispatch d
        JOIN model_run r ON r.run_id = d.run_id
        JOIN battery_spec b ON b.battery_id = r.battery_id
        WHERE d.soc_mwh < b.min_soc_mwh - 1e-6
        GROUP BY d.run_id
    """,
    "flow_above_power_rating": """
        SELECT d.run_id, count(*) AS violations,
               max(greatest(d.charge_mw, d.discharge_mw) - b.power_mw) AS worst
        FROM dispatch d
        JOIN model_run r ON r.run_id = d.run_id
        JOIN battery_spec b ON b.battery_id = r.battery_id
        WHERE greatest(d.charge_mw, d.discharge_mw) > b.power_mw + 1e-6
        GROUP BY d.run_id
    """,
    "dispatch_outside_run_window": """
        SELECT d.run_id, count(*) AS violations, NULL::double precision AS worst
        FROM dispatch d
        JOIN model_run r ON r.run_id = d.run_id
        JOIN settlement_period sp ON sp.time_id = d.time_id
        WHERE sp.datetime < r.period_start OR sp.datetime >= r.period_end
        GROUP BY d.run_id
    """,
}

# Float comparisons carry a 1e-6 tolerance throughout. A solver returns values good to
# its own tolerance, not to the last bit, so an exact comparison would report a violation
# on a schedule that is correct to any meaningful precision.


def check(engine, run_id=None):
    """Return {invariant: [rows]} for every invariant that is broken. Empty means clean."""
    failures = {}
    with engine.connect() as con:
        for name, sql in INVARIANTS.items():
            query = sql if run_id is None else sql.replace(
                "GROUP BY d.run_id", f"AND d.run_id = {int(run_id)} GROUP BY d.run_id"
            )
            rows = con.execute(text(query)).mappings().all()
            if rows:
                failures[name] = [dict(r) for r in rows]
    return failures


def assert_valid(engine, run_id=None):
    """Raise if any invariant is broken. Called by the harness before a run is kept."""
    failures = check(engine, run_id)
    if failures:
        detail = "\n".join(
            f"  {name}: {rows}" for name, rows in failures.items()
        )
        raise ValueError(f"dispatch violates physical constraints:\n{detail}")
