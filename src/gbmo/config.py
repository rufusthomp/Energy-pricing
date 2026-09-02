"""Paths and constants shared across the package.

Everything is resolved from this file's own location rather than the working
directory. The pre-package layout required `python load.py` to be run from `src/`
because its paths were relative strings; that breaks as soon as tests, a scheduler
or a container invoke the ETL from somewhere else.
"""

from pathlib import Path

# src/gbmo/config.py -> src/gbmo -> src -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
COMMODITY_DIR = RAW_DIR / "commodity"
DEMAND_DIR = RAW_DIR / "demand"

SCHEMA_PATH = REPO_ROOT / "schema.sql"
DB_PATH = DATA_DIR / "gb-merit-order.db"

# Source files
GENERATION_CSV = RAW_DIR / "df_fuel_ckan.csv"
PRICE_CSV = RAW_DIR / "price_mid.csv"
DEMAND_GLOB = "demanddata_*.csv"

# Matches the start of the generation and demand data. Commodity series are trimmed
# to this so the modelled span never runs ahead of the observations it prices.
FIRST_YEAR = 2009
