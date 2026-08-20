-- ============================================================================
-- V1 — static marginal cost (fuel.mc is a single fixed number per fuel)
-- Kept as the baseline the v2 queries below are measured against.
-- ============================================================================

-- Gives the price-setting fuel for each time period
WITH stack AS (
   SELECT fuel.name, fuel.mc, generation.mw, demand.nd, demand.tsd, time.datetime, time.time_id,
SUM(mw) OVER (PARTITION BY time.time_id ORDER BY mc) AS cumulative_supply FROM generation
INNER JOIN fuel ON generation.fuel_id = fuel.fuel_id
    INNER JOIN time ON time.time_id = generation.time_id
		INNER JOIN demand on demand.time_id = generation.time_id
), 
qualifying AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY time_id ORDER BY mc) AS rn
    FROM stack
    WHERE cumulative_supply >= tsd
)
SELECT * FROM qualifying WHERE rn = 1;


-- Difference in modelled price vs. actual
WITH stack AS (
   SELECT fuel.name, fuel.mc, generation.mw, demand.nd, demand.tsd, time.datetime, time.time_id,
SUM(mw) OVER (PARTITION BY time.time_id ORDER BY mc) AS cumulative_supply FROM generation
INNER JOIN fuel ON generation.fuel_id = fuel.fuel_id
    INNER JOIN time ON time.time_id = generation.time_id
		INNER JOIN demand on demand.time_id = generation.time_id
), 
qualifying AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY time_id ORDER BY mc) AS rn
    FROM stack
    WHERE cumulative_supply >= tsd
)
SELECT qualifying.datetime, qualifying.name AS marginal_fuel, qualifying.mc AS modelled_price, price.price AS actual_mid, price.price - qualifying.mc AS error FROM qualifying
    JOIN price ON price.time_id = qualifying.time_id
    WHERE rn = 1;


-- Show generation mix evolving over time
SELECT AVG(generation.mw) AS average_mw, fuel.name, time.year FROM generation
INNER JOIN fuel on generation.fuel_id = fuel.fuel_id
    INNER JOIN time on generation.time_id = time.time_id
    GROUP BY time.year, fuel.name
    ORDER BY time.year;


-- ============================================================================
-- V2 — time-varying short-run marginal cost
--
-- SRMC per MWh of electricity, for a thermal fuel in a given month:
--
--     fuel_cost   = (p_kWh_GCV * 1.108 * 10) / efficiency
--     carbon_cost = (carbon_factor / 1000) * carbon_GBP_per_tonne
--     srmc        = fuel_cost + carbon_cost
--
--   * 10     p/kWh -> GBP/MWh
--   * 1.108  GCV -> LHV. UK gas is billed on a gross calorific basis but plant
--            efficiency is quoted net, so the price is restated before it meets
--            fuel.efficiency. Skipping this understates gas by ~10%.
--   / 1000   fuel.carbon_factor is kgCO2/MWh_e, allowance prices are per tonne.
--
-- Everything below is computed at query time from series stored as observed.
-- The three modelling choices live here, not in the data:
--   1. the EUA -> UKA splice        (the COALESCE in `carbon`)
--   2. whether CPS is added         (the + in `carbon`)
--   3. which gas series to price on (the COALESCE in `srmc`)
-- ============================================================================

-- The effective GB carbon price for each month: traded allowance + CPS top-up.
-- COALESCE lands the EUA -> UKA splice on the right month without a hardcoded
-- date: UKA only exists from 2021-05 and is preferred wherever both are present.
WITH carbon AS (
    SELECT year, month,
           COALESCE(MAX(CASE WHEN source = 'uka' THEN price END),
                    MAX(CASE WHEN source = 'eua' THEN price END))
             + MAX(CASE WHEN source = 'cps' THEN price END) AS carbon_price
    FROM commodity_price
    WHERE commodity = 'carbon'
    GROUP BY year, month
),
-- One row per (fuel, month) so every fuel has a price in every modelled month,
-- including the eight with no commodity series behind them.
month_fuel AS (
    SELECT m.year, m.month,
           fuel.fuel_id, fuel.mc, fuel.carbon_factor, fuel.efficiency, fuel.commodity
    FROM (SELECT DISTINCT year, month FROM time) m
    CROSS JOIN fuel
),
srmc AS (
    SELECT mf.year, mf.month, mf.fuel_id,
           -- Outer COALESCE is the fallback to the v1 static cost, and covers three
           -- cases at once: fuels with no commodity (commodity IS NULL never joins),
           -- the suppressed 2023 Q3 coal quarter, and every month after the
           -- commodity series end (carbon stops 2026-03), where a NULL carbon price
           -- would otherwise make the whole expression NULL.
           COALESCE(
               (COALESCE(sap.price, qep.price) * 1.108 * 10.0) / mf.efficiency
                 + (mf.carbon_factor / 1000.0) * c.carbon_price,
               mf.mc
           ) AS srmc
    FROM month_fuel mf
    -- Both joins pin `source`. Without that, commodity = 'gas' matches two rows per
    -- month and the fuel silently appears twice in the stack below, double-counting
    -- its capacity in the cumulative sum.
    LEFT JOIN commodity_price qep
           ON qep.commodity = mf.commodity AND qep.source = 'qep'
          AND qep.year = mf.year AND qep.month = mf.month
    LEFT JOIN commodity_price sap
           ON sap.commodity = mf.commodity AND sap.source = 'sap'
          AND sap.year = mf.year AND sap.month = mf.month
    LEFT JOIN carbon c
           ON c.year = mf.year AND c.month = mf.month
),
-- Same shape as the v1 stack, but ordered on the computed SRMC instead of the
-- fixed fuel.mc. Both window functions must order on the same key: dispatch order
-- and "cheapest qualifying" have to agree or the marginal fuel is wrong.
dynamic_stack AS (
    SELECT time.time_id, time.datetime, time.year, fuel.name,
           srmc.srmc, generation.mw, demand.tsd,
           SUM(generation.mw) OVER (PARTITION BY time.time_id ORDER BY srmc.srmc) AS cumulative_supply
    FROM generation
    INNER JOIN fuel   ON generation.fuel_id = fuel.fuel_id
    INNER JOIN time   ON time.time_id = generation.time_id
    INNER JOIN demand ON demand.time_id = generation.time_id
    INNER JOIN srmc   ON srmc.fuel_id = generation.fuel_id
                     AND srmc.year = time.year AND srmc.month = time.month
),
dynamic_marginal AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY time_id ORDER BY srmc) AS rn
    FROM dynamic_stack
    WHERE cumulative_supply >= tsd
)
SELECT datetime, name AS marginal_fuel, ROUND(srmc, 2) AS modelled_price
FROM dynamic_marginal
WHERE rn = 1;


-- Modelled vs actual, v1 against v2, by year. Runs both stacks and joins them on
-- the settlement period, so the two models are compared on identical periods even
-- where they disagree about which fuel is marginal.
WITH carbon AS (
    SELECT year, month,
           COALESCE(MAX(CASE WHEN source = 'uka' THEN price END),
                    MAX(CASE WHEN source = 'eua' THEN price END))
             + MAX(CASE WHEN source = 'cps' THEN price END) AS carbon_price
    FROM commodity_price
    WHERE commodity = 'carbon'
    GROUP BY year, month
),
srmc AS (
    SELECT mf.year, mf.month, mf.fuel_id,
           COALESCE(
               (COALESCE(sap.price, qep.price) * 1.108 * 10.0) / mf.efficiency
                 + (mf.carbon_factor / 1000.0) * c.carbon_price,
               mf.mc
           ) AS srmc
    FROM (SELECT m.year, m.month,
                 fuel.fuel_id, fuel.mc, fuel.carbon_factor, fuel.efficiency, fuel.commodity
          FROM (SELECT DISTINCT year, month FROM time) m
          CROSS JOIN fuel) mf
    LEFT JOIN commodity_price qep
           ON qep.commodity = mf.commodity AND qep.source = 'qep'
          AND qep.year = mf.year AND qep.month = mf.month
    LEFT JOIN commodity_price sap
           ON sap.commodity = mf.commodity AND sap.source = 'sap'
          AND sap.year = mf.year AND sap.month = mf.month
    LEFT JOIN carbon c ON c.year = mf.year AND c.month = mf.month
),
dynamic_stack AS (
    SELECT time.time_id, time.year, srmc.srmc, demand.tsd,
           SUM(generation.mw) OVER (PARTITION BY time.time_id ORDER BY srmc.srmc) AS cumulative_supply
    FROM generation
    INNER JOIN fuel   ON generation.fuel_id = fuel.fuel_id
    INNER JOIN time   ON time.time_id = generation.time_id
    INNER JOIN demand ON demand.time_id = generation.time_id
    INNER JOIN srmc   ON srmc.fuel_id = generation.fuel_id
                     AND srmc.year = time.year AND srmc.month = time.month
),
dynamic_marginal AS (
    SELECT time_id, year, srmc, ROW_NUMBER() OVER (PARTITION BY time_id ORDER BY srmc) AS rn
    FROM dynamic_stack WHERE cumulative_supply >= tsd
),
static_stack AS (
    SELECT time.time_id, fuel.mc, demand.tsd,
           SUM(generation.mw) OVER (PARTITION BY time.time_id ORDER BY fuel.mc) AS cumulative_supply
    FROM generation
    INNER JOIN fuel   ON generation.fuel_id = fuel.fuel_id
    INNER JOIN time   ON time.time_id = generation.time_id
    INNER JOIN demand ON demand.time_id = generation.time_id
),
static_marginal AS (
    SELECT time_id, mc, ROW_NUMBER() OVER (PARTITION BY time_id ORDER BY mc) AS rn
    FROM static_stack WHERE cumulative_supply >= tsd
)
SELECT dynamic_marginal.year,
       COUNT(*)                                                     AS periods,
       ROUND(AVG(price.price), 1)                                   AS actual_mid,
       ROUND(AVG(static_marginal.mc), 1)                            AS modelled_v1,
       ROUND(AVG(dynamic_marginal.srmc), 1)                         AS modelled_v2,
       ROUND(AVG(static_marginal.mc) - AVG(price.price), 1)         AS error_v1,
       ROUND(AVG(dynamic_marginal.srmc) - AVG(price.price), 1)      AS error_v2
FROM dynamic_marginal
INNER JOIN static_marginal ON static_marginal.time_id = dynamic_marginal.time_id
                          AND static_marginal.rn = 1
INNER JOIN price ON price.time_id = dynamic_marginal.time_id
WHERE dynamic_marginal.rn = 1
GROUP BY dynamic_marginal.year
ORDER BY dynamic_marginal.year;
