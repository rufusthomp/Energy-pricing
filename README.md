Dropped _perc as low amount of data so calculation is simple.
Don't store derived data. 
We keep dervied day, month, year, season as they are immutable and will not suffer from update anomalies. 

Source: https://www.sqe.energy/insights/understanding-power-markets-merit-order-and-marginal-pricing, 

Why use time table with time_id instead of using time string as foreign_id?

We may want to group by seasons and this is a custom rule. In a time table this can be defined once to ensure consistency. 

Integer joins are cheaper than matching on a string timestamp. 

This is traded off with an additional join on most queries. 

Settlement period - Each day is divided into numebered settlment periods. Settled in half-hourly blocks (48 total). Period 1 = 00:00 - 00:30, period 2 = 00:30 - 01:00,..., period 48 = 23:30 - 24:00

Setup is reproducible as .db is disposable. Running load.py regenerates the db from schema.sql