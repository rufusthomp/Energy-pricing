import sqlite3
import pandas as pd
import glob

with open(r"..\schema.sql") as f:
    schema_sql = f.read()

con = sqlite3.connect(r"..\data\gb-merit-order.db")

con.executescript(schema_sql)

# efficiency is LHV basis and is not independent of carbon_factor: the chemistry fixes
# emissions per MWh of *heat* (gas 202, coal 341 kgCO2/MWh_th), so
# carbon_factor = heat_emissions / efficiency. Gas 0.50 and coal 0.36 are GB fleet
# averages over the period; the factors below are derived from them, not chosen freely.
# mc stays as the v1 static cost and is still the price for every fuel with commodity NULL.
fuels = [
    ('WIND', 0, 0, None, None, 0),
    ('WIND_EMB', 0, 0, None, None, 0),
    ('SOLAR', 0, 0, None, None, 0),
    ('HYDRO', 5, 0, None, None, 1), # Non-zero MC as opp. cost of releasing water now vs. later
    ('NUCLEAR', 10, 0, None, None, 1),
    ('BIOMASS', 45, 0, None, None, 1), # Carbon factor = 0 for costing model as ETS factor = 0 however real emissions high
    ('GAS', 70, 404, 0.50, 'gas', 1),
    ('COAL', 110, 946, 0.36, 'coal', 1),
    ('IMPORTS', 50, 0, None, None, 1), # Flows when domestic is expensive so sits just below gas. Carbon 0 by territorial convention
    ('STORAGE', 120, 0, None, None, 1), # Used only when domestic price is high
    ('OTHER', 100, 400, None, None, 1) # Mixed bag, no single commodity to drive it
    ]

insert_fuels = '''INSERT INTO fuel (name, mc, carbon_factor, efficiency, commodity, is_dispatchable)
            VALUES (?, ?, ?, ?, ?, ?)'''

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

# Keep only columns in generation
df = df[['time_id', 'fuel_id', 'mw']]
# Send data to generation
df.to_sql('generation', con, if_exists='append', index=False)

'''Demand Table'''

# Concatenate the 18 demand files, one for each year 2009-2026
demand_files = glob.glob(r"..\data\raw\demand\demanddata_*.csv")
demand_df = pd.concat([pd.read_csv(f) for f in demand_files], ignore_index=True)
demand_df.head()

# Convert settlement date into ISO format and add settlement periods converted to time
demand_df['datetime'] = (
    pd.to_datetime(demand_df['SETTLEMENT_DATE'])
    + pd.to_timedelta((demand_df['SETTLEMENT_PERIOD'] - 1) * 30, unit='m')
).dt.strftime('%Y-%m-%dT%H:%M:%S')

demand_df = demand_df.merge(time_lookup, on='datetime')
demand_df = demand_df[['time_id', 'ND', 'TSD']]
demand_df.columns = demand_df.columns.str.lower() # Fit naming schema
demand_df = demand_df.drop_duplicates(subset='time_id')

demand_df.to_sql('demand', con, if_exists='append', index=False)

'''Price Table'''

price_data = pd.read_csv(r"..\data\raw\price_mid.csv")
price_df = pd.DataFrame(price_data)

price_df['pv'] = price_df['price'] * price_df['volume']
grouped_price_df = price_df.groupby('startTime', as_index=False)[['pv', 'volume']].sum()
grouped_price_df['price'] = grouped_price_df['pv'] / grouped_price_df['volume']
grouped_price_df = grouped_price_df.dropna(subset=['price'])
grouped_price_df['startTime'] = pd.to_datetime(grouped_price_df['startTime']).dt.strftime('%Y-%m-%dT%H:%M:%S')
grouped_price_df = grouped_price_df.merge(time_lookup, left_on='startTime', right_on='datetime')
grouped_price_df = grouped_price_df[['time_id', 'price']]
grouped_price_df = grouped_price_df.drop_duplicates(subset='time_id')
grouped_price_df.to_sql('price', con, if_exists='append', index=False)

'''Commodity Price Table'''

# Every series is loaded as observed, on a monthly grain, and kept separate from every
# other one. The EUA->UKA splice, whether CPS is added, and QEP vs SAP for gas are all
# modelling choices made at query time, so nothing here is pre-combined. The one
# conversion applied is EUR->GBP on the EUA series, which is a unit change, not a
# modelling choice — the FX series itself is loaded too so that step stays auditable.

FIRST_YEAR = 2009 # Matches the start of the generation and demand data

def quarterly_to_monthly(path, value_col):
    """QEP is quarterly; repeat each quarter's price across its three months."""
    q = pd.read_csv(path)
    q = q.loc[q['year'] >= FIRST_YEAR, ['year', 'quarter', value_col]].reset_index(drop=True)
    q = q.loc[q.index.repeat(3)].copy()
    q['month'] = (q['quarter'] - 1) * 3 + 1 + q.groupby(level=0).cumcount()
    return q.rename(columns={value_col: 'price'})[['year', 'month', 'price']]

def daily_to_monthly(path, value_col):
    """Daily end-of-day series -> mean over each calendar month."""
    d = pd.read_csv(path, parse_dates=['date'])
    d = d[d['date'].dt.year >= FIRST_YEAR].copy()
    d['year'] = d['date'].dt.year
    d['month'] = d['date'].dt.month
    d = d.groupby(['year', 'month'], as_index=False)[value_col].mean()
    return d.rename(columns={value_col: 'price'})

def year_month_to_monthly(path, month_col, value_col):
    """A series already published monthly, keyed 'YYYY-MM'."""
    m = pd.read_csv(path)
    parsed = pd.to_datetime(m[month_col])
    m['year'] = parsed.dt.year
    m['month'] = parsed.dt.month
    m = m[m['year'] >= FIRST_YEAR]
    return m.rename(columns={value_col: 'price'})[['year', 'month', 'price']]

# Carbon Price Support: a fixed statutory schedule, not a dataset. Financial years run
# from 1 April, and it is £0 before April 2013. Frozen at £18/tCO2 since April 2016 —
# that freeze, not the allowance price, is what kept coal uneconomic through the 2010s.
CPS_SCHEDULE = [(2013, 4.94), (2014, 9.55), (2015, 18.08), (2016, 18.00)]

def cps_rate(year, month):
    financial_year = year if month >= 4 else year - 1
    rate = 0.0
    for start_year, value in CPS_SCHEDULE:
        if financial_year >= start_year:
            rate = value
    return rate

commodity_dir = r"..\data\raw\commodity"

gas_qep = quarterly_to_monthly(rf"{commodity_dir}\gas_price_qep_321.csv", 'gas_pence_per_kwh_gcv')
coal_qep = quarterly_to_monthly(rf"{commodity_dir}\coal_price_qep_321.csv", 'coal_pence_per_kwh_gcv')
gas_sap = year_month_to_monthly(rf"{commodity_dir}\gas_sap_monthly_ons.csv", 'month', 'sap_pence_per_kwh')
fx = year_month_to_monthly(rf"{commodity_dir}\fx_eur_gbp_monthly_ecb.csv", 'month', 'gbp_per_eur')
uka = daily_to_monthly(rf"{commodity_dir}\uka_price_daily_icap.csv", 'price_gbp')

# EUA is quoted in EUR, so it needs the ECB rate before it can sit alongside UKA in GBP
eua = daily_to_monthly(rf"{commodity_dir}\eua_price_daily_icap.csv", 'price_eur')
eua = eua.merge(fx.rename(columns={'price': 'gbp_per_eur'}), on=['year', 'month'])
eua['price'] = eua['price'] * eua['gbp_per_eur']
eua = eua[['year', 'month', 'price']]

# CPS covers every month in the modelled span so the query never hits a missing top-up
cps = pd.DataFrame(
    [(y, m) for y in range(FIRST_YEAR, 2027) for m in range(1, 13)],
    columns=['year', 'month'])
cps['price'] = [cps_rate(y, m) for y, m in zip(cps['year'], cps['month'])]

PENCE_PER_KWH = 'pence_per_kWh_GCV'
GBP_PER_TCO2 = 'GBP_per_tCO2'

series = [
    (gas_qep, 'gas', 'qep', PENCE_PER_KWH),
    (gas_sap, 'gas', 'sap', PENCE_PER_KWH),
    (coal_qep, 'coal', 'qep', PENCE_PER_KWH),
    (eua, 'carbon', 'eua', GBP_PER_TCO2),
    (uka, 'carbon', 'uka', GBP_PER_TCO2),
    (cps, 'carbon', 'cps', GBP_PER_TCO2),
    (fx, 'fx', 'ecb', 'GBP_per_EUR'),
    ]

commodity_frames = []
for frame, commodity, source, unit in series:
    frame = frame.copy()
    frame['commodity'] = commodity
    frame['source'] = source
    frame['unit'] = unit
    commodity_frames.append(frame[['year', 'month', 'commodity', 'source', 'price', 'unit']])

commodity_df = pd.concat(commodity_frames, ignore_index=True)
commodity_df.to_sql('commodity_price', con, if_exists='append', index=False)

con.commit()
con.close()