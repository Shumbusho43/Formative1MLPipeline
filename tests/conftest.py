"""Keep tests off the real (hosted) databases configured in .env.

These run before `api` is imported; load_dotenv() does not override variables that are already set.
"""
import os

os.environ["SQL_DATABASE_URL"] = "sqlite://"
os.environ["SQL_SSL"] = "false"
os.environ["MONGO_URI"] = "mongodb://localhost:1"  # never contacted: tests inject mongomock
