-- Dimension: one row per fuel type. Hand-curated modelling layer (mc, carbon_factor
-- are assumptions, not observations) kept separate from the observed facts.

DROP TABLE IF EXISTS fuel;
CREATE TABLE fuel (
    fuel_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    mc REAL NOT NULL,            -- static SRMC (v1). Still the price for fuels with no commodity series
    carbon_factor REAL NOT NULL, -- kgCO2 per MWh of *electricity* = heat emissions / efficiency
    efficiency REAL,             -- LHV basis. NULL where there is no fuel cost to model
    commodity TEXT,              -- 'gas' | 'coal'. NULL = no commodity series, fall back to mc
    is_dispatchable INTEGER NOT NULL
);

-- Dimension: one row per half-hourly settlement period. Calendar attributes are stored
-- (not derived at query time) because a calendar is immutable: no update-anomaly risk.

DROP TABLE IF EXISTS time;
CREATE TABLE time (
    time_id INTEGER PRIMARY KEY,
    datetime TEXT UNIQUE NOT NULL,
    date TEXT NOT NULL,
    month INTEGER NOT NULL,
    year INTEGER NOT NULL,
    season TEXT NOT NULL
);

-- One row = MW of one fuel at one time period

DROP TABLE IF EXISTS generation;

CREATE TABLE generation ( 
    time_id INTEGER NOT NULL REFERENCES time(time_id),
    fuel_id INTEGER NOT NULL REFERENCES fuel(fuel_id),
    mw REAL NOT NULL,
    PRIMARY KEY (time_id, fuel_id)
);
-- Composite PK uses leftmost-prefix convention so create an index for fuel_id for fuel-only aggregations
CREATE INDEX idx_generation_fuel_id ON generation(fuel_id);

-- One row = demand at one time

DROP TABLE IF EXISTS demand;
CREATE TABLE demand (
    time_id INTEGER NOT NULL REFERENCES time(time_id),
    nd REAL NOT NULL, -- National Demand
    tsd REAL NOT NULL, -- Transmission System Demand the more defensible choice as ND would bias our price down
    PRIMARY KEY (time_id)
);

-- One row = actual price paid at one time
-- The difference between modelled and real price divergence signals balancing actions

DROP TABLE IF EXISTS price;
CREATE TABLE price (
    time_id INTEGER NOT NULL REFERENCES time(time_id),
    price REAL NOT NULL,
    PRIMARY KEY (time_id)
);

-- V2: dynamic marginal cost. Monthly commodity prices so the SRMC of the thermal fuels
-- can be computed at query time instead of using the static fuel.mc.
--
-- Every series is stored as observed and separately from every other: the EUA->UKA splice
-- date, whether CPS is added, and whether gas comes from QEP or SAP are all *modelling*
-- choices, so they belong in the query, not baked into the data. `source` keeps two
-- series for the same commodity apart (gas has both QEP and SAP), which is what makes
-- the choice a query-time one.
--
-- Grain is monthly: the finest grain shared by enough of the series to join on. QEP is
-- natively quarterly and is repeated across the months of its quarter; the daily carbon
-- and FX series are monthly means. Units differ by commodity, hence the unit column --
-- never sum or compare across commodities without reading it.

DROP TABLE IF EXISTS commodity_price;
CREATE TABLE commodity_price (
	year INTEGER NOT NULL,
	month INTEGER NOT NULL,
	commodity TEXT NOT NULL, -- 'gas' | 'coal' | 'carbon' | 'fx'  (joins to fuel.commodity)
	source TEXT NOT NULL,    -- 'qep' | 'sap' | 'eua' | 'uka' | 'cps' | 'ecb'
	price REAL NOT NULL,
	unit TEXT NOT NULL,      -- 'pence_per_kWh_GCV' | 'GBP_per_tCO2' | 'GBP_per_EUR'
	PRIMARY KEY (year, month, commodity, source)
);
