"""Runtime configuration, read from environment variables (or a .env file)."""
import os

from dotenv import load_dotenv

load_dotenv()

# SQLAlchemy URL for the relational database (Task 2 MySQL schema).
#   MySQL : mysql+pymysql://user:password@localhost:3306/beijing_air_quality
#   SQLite: sqlite:///./beijing_air_quality.db   (handy fallback for local dev/tests)
SQL_DATABASE_URL = os.getenv("SQL_DATABASE_URL", "sqlite:///./beijing_air_quality.db")

# Hosted MySQL (e.g. Aiven) requires TLS. SQL_SSL=true encrypts the connection
# (like --ssl-mode=REQUIRED); also set SQL_SSL_CA to the provider's ca.pem to verify the server.
SQL_SSL = os.getenv("SQL_SSL", "false").lower() in ("1", "true", "yes")
SQL_SSL_CA = os.getenv("SQL_SSL_CA") or None

# MongoDB connection (Task 2 collection design).
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "beijing_air_quality")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "air_quality_readings")

# Upper bound on rows returned by list / date-range endpoints.
MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", "5000"))
