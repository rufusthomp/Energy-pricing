import sqlite3
import pandas as pd

with open(r"..\schema.sql") as f:
    schema_sql = f.read()

con = sqlite3.connect(r"..\data\gb-merit-order.db")

con.executescript(schema_sql)

fuels = [
    ('WIND', 0, 0, 0),
    ('WIND_EMB', 0, 0, 0),
    ('SOLAR', 0, 0, 0),
    ('HYDRO', 5, 0, 1), # Non-zero MC as opp. cost of releasing water now vs. later
    ('NUCLEAR', 10, 0, 1),
    ('BIOMASS', 45, 0, 1), # Carbon factor = 0 for costing model as ETS factor = 0 however real emissions high
    ('GAS', 70, 350, 1),
    ('COAL', 110, 900, 1),
    ('IMPORTS', 50, 0, 1), # Flows when domestic is expensive so sits just below gas. Carbon 0 by territorial convention
    ('STORAGE', 120, 0, 1), # Used only when domestic price is high
    ('OTHER', 100, 400, 1) #
    ]

insert_fuels = '''INSERT INTO fuel (name, mc, carbon_factor, is_dispatchable)
            VALUES (?, ?, ?, ?)'''

con.executemany(insert_fuels, fuels)

df = pd.read_csv(r"..\data\raw\df_fuel_ckan.csv")

# Drop derived data
df = df.drop(columns=['GENERATION','CARBON_INTENSITY', 
       'LOW_CARBON', 'ZERO_CARBON', 'RENEWABLE', 'FOSSIL',
       'GAS_perc', 'COAL_perc', 'NUCLEAR_perc', 'WIND_perc', 'WIND_EMB_perc',
       'HYDRO_perc', 'IMPORTS_perc', 'BIOMASS_perc', 'OTHER_perc',
       'SOLAR_perc', 'STORAGE_perc', 'GENERATION_perc', 'LOW_CARBON_perc',
       'ZERO_CARBON_perc', 'RENEWABLE_perc', 'FOSSIL_perc'], axis=1)

# Prepare data for time table
time_df = pd.DataFrame({'datetime': df['DATETIME'].drop_duplicates()})
parsed = pd.to_datetime(time_df['datetime'])

time_df['date'] = parsed.dt.strftime('%Y-%m-%d')
time_df['month'] = parsed.dt.month
time_df['year'] = parsed.dt.year

month_to_season = {12:'winter', 1:'winter', 2:'winter', 3:'spring', 4:'spring', 5:'spring', 6:'summer', 7:'summer', 8:'summer', 9:'autumn', 10:'autumn', 11:'autumn'}
time_df['season'] = time_df['month'].map(month_to_season)

time_df.to_sql('time', con, if_exists='append', index=False)

# Convert wide df to long
df = pd.melt(df, id_vars='DATETIME', var_name='name', value_name='mw')


fuel_lookup = pd.read_sql('SELECT fuel_id, name FROM fuel', con)
time_lookup = pd.read_sql('SELECT time_id, datetime FROM time', con)

df = df.merge(time_lookup, left_on='DATETIME', right_on='datetime')
df = df.merge(fuel_lookup, on='name')
# Ensure successful melt and merge
print(df.shape)
print(df.columns)

# Keep only columns in generation
df = df[['time_id', 'fuel_id', 'mw']]
# Send data to generation
df.to_sql('generation', con, if_exists='append', index=False)

con.commit()
con.close()