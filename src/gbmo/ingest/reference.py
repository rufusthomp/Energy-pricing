"""The hand-curated modelling layer.

These are assumptions, not observations, which is why they live in code and load into
the `ref.fuel` dimension rather than arriving from a source file. Keeping them separate
from the observed facts is the point of the split.
"""

# efficiency is LHV basis and is not independent of carbon_factor: the chemistry fixes
# emissions per MWh of *heat* (gas 202, coal 341 kgCO2/MWh_th), so
# carbon_factor = heat_emissions / efficiency. Gas 0.50 and coal 0.36 are GB fleet
# averages over the period; the factors below are derived from them, not chosen freely.
# mc stays as the v1 static cost and is still the price for every fuel with commodity NULL.
FUELS = [
    ("WIND", 0, 0, None, None, False),
    ("WIND_EMB", 0, 0, None, None, False),
    ("SOLAR", 0, 0, None, None, False),
    ("HYDRO", 5, 0, None, None, True),      # Non-zero MC as opp. cost of releasing water now vs. later
    ("NUCLEAR", 10, 0, None, None, True),
    ("BIOMASS", 45, 0, None, None, True),   # Carbon factor = 0 for costing model as ETS factor = 0 however real emissions high
    ("GAS", 70, 404, 0.50, "gas", True),
    ("COAL", 110, 946, 0.36, "coal", True),
    ("IMPORTS", 50, 0, None, None, True),   # Flows when domestic is expensive so sits just below gas. Carbon 0 by territorial convention
    ("STORAGE", 120, 0, None, None, True),  # Used only when domestic price is high
    ("OTHER", 100, 400, None, None, True),  # Mixed bag, no single commodity to drive it
]

# Derived columns dropped on load: everything here is recomputable in SQL from the
# observed MW values, so storing it would duplicate state that can drift.
GENERATION_DERIVED_COLUMNS = [
    "GENERATION", "CARBON_INTENSITY",
    "LOW_CARBON", "ZERO_CARBON", "RENEWABLE", "FOSSIL",
    "GAS_perc", "COAL_perc", "NUCLEAR_perc", "WIND_perc", "WIND_EMB_perc",
    "HYDRO_perc", "IMPORTS_perc", "BIOMASS_perc", "OTHER_perc",
    "SOLAR_perc", "STORAGE_perc", "GENERATION_perc", "LOW_CARBON_perc",
    "ZERO_CARBON_perc", "RENEWABLE_perc", "FOSSIL_perc",
]
