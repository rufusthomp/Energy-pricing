-- 

DROP TABLE IF EXISTS fuel;
CREATE TABLE fuel (
    fuel_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    mc REAL NOT NULL,
    carbon_factor REAL NOT NULL,
    is_dispatchable INTEGER NOT NULL
);

-- 

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

-- One row = demand at one time

DROP TABLE IF EXISTS demand;
CREATE TABLE demand (
    time_id INTEGER NOT NULL REFERENCES time(time_id),
    demand REAL NOT NULL,
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