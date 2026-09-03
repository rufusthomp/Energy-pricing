"""Paths, database URL and constants shared across the package.

Paths are resolved from this file's own location rather than the working directory.
The pre-package layout required `python load.py` to be run from `src/` because its
paths were relative strings; that breaks as soon as tests, a scheduler or a container
invoke the ETL from somewhere else.
"""

import os
from pathlib import Path

# src/gbmo/config.py -> src/gbmo -> src -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
COMMODITY_DIR = RAW_DIR / "commodity"
DEMAND_DIR = RAW_DIR / "demand"

# The pre-Postgres SQLite build. Retained only so a migration can be diffed against a
# known-good database; nothing writes to it any more.
LEGACY_SQLITE_PATH = DATA_DIR / "gb-merit-order.db"

# Defaults to the local Postgres in docker-compose.yml. Override to point elsewhere.
DATABASE_URL = os.environ.get(
    "GBMO_DATABASE_URL",
    "postgresql+psycopg://gbmo:gbmo@localhost:5432/gbmo",
)

# Source files
GENERATION_CSV = RAW_DIR / "df_fuel_ckan.csv"
PRICE_CSV = RAW_DIR / "price_mid.csv"
DEMAND_GLOB = "demanddata_*.csv"

# Matches the start of the generation and demand data. Commodity series are trimmed
# to this so the modelled span never runs ahead of the observations it prices.
FIRST_YEAR = 2009

# Market Index Price coverage begins in 2018, so anything that has to line up with a
# price (weather, the arbitrage study) starts there rather than at FIRST_YEAR.
FIRST_PRICE_YEAR = 2018
LAST_YEAR = 2026
