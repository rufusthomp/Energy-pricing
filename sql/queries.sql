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
