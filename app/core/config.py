import os
from datetime import timedelta

# --- Database ---
# Defaults to local SQLite so the project runs with zero external setup.
# Set DATABASE_URL env var to point at Postgres in production, e.g.:
# postgresql+psycopg2://user:password@localhost:5432/fraud_platform
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fraud_platform.db")

# --- Auth / JWT ---
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_use_env_var")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# --- API keys for machine-to-machine transaction ingestion ---
# Each business gets an API key (stored hashed) used in the
# X-API-Key header when POSTing transactions programmatically.
API_KEY_HEADER_NAME = "X-API-Key"

# --- CSV import ---
MAX_CSV_ROWS_PER_IMPORT = int(os.getenv("MAX_CSV_ROWS_PER_IMPORT", "50000"))
