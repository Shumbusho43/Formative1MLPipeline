"""Load the Beijing Multi-Site Air Quality CSVs into the SQL database and MongoDB.

Uses the Task 2 schemas. Run from the repo root:

    python -m database.load_data --data-dir data/raw            # both databases, all stations
    python -m database.load_data --target mongo --stations Dongsi
    python -m database.load_data --reset                         # wipe existing readings first
"""
import argparse
import glob
import math
import os
import re
import time

import pandas as pd
from pymongo import MongoClient

from api import config
from api.mongo_db import ensure_indexes, to_document
from api.sql_db import PollutantReference, Reading, SessionLocal, Station, engine, init_db

# Raw CSV column  ->  API / database field
COLUMN_MAP = {
    "PM2.5": "pm25", "PM10": "pm10", "SO2": "so2", "NO2": "no2", "CO": "co", "O3": "o3",
    "TEMP": "temp", "PRES": "pres", "DEWP": "dewp", "RAIN": "rain",
    "wd": "wind_direction", "WSPM": "wind_speed",
}

# WHO 2021 guidelines, as seeded in Task 2.
POLLUTANTS = [
    ("PM2.5", "Fine Particulate Matter", "μg/m³", 5.0, 15.0,
     "Particles ≤ 2.5 μm. Penetrate deep into lungs; linked to cardiovascular disease."),
    ("PM10", "Coarse Particulate Matter", "μg/m³", 15.0, 45.0,
     "Particles ≤ 10 μm. Irritate the upper respiratory tract."),
    ("SO2", "Sulfur Dioxide", "μg/m³", None, 40.0,
     "Emitted by burning fossil fuels; precursor to acid rain and PM2.5 formation."),
    ("NO2", "Nitrogen Dioxide", "μg/m³", 10.0, 25.0,
     "Produced by traffic and combustion; irritates airways and contributes to smog."),
    ("CO", "Carbon Monoxide", "μg/m³", None, 4000.0,
     "Colorless, odorless gas from incomplete combustion; reduces blood O₂ capacity."),
    ("O3", "Ground-level Ozone", "μg/m³", None, 100.0,
     "Formed by photochemical reactions involving NO2 and VOCs; damages lung tissue."),
]

BATCH = 10_000


def load_csvs(data_dir: str, stations=None) -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(data_dir, "**", "*.csv"), recursive=True))
    if not files:
        raise FileNotFoundError(f"No CSV files found under {data_dir}. Unzip the Kaggle archive there.")
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    if stations:
        df = df[df["station"].isin(stations)]
    df["timestamp"] = pd.to_datetime(df[["year", "month", "day", "hour"]])
    df = df.rename(columns=COLUMN_MAP)
    df = df[["station", "timestamp", *COLUMN_MAP.values()]]
    df = df.drop_duplicates(subset=["station", "timestamp"]).sort_values(["station", "timestamp"])
    print(f"Loaded {len(df):,} rows from {len(files)} files "
          f"({df['timestamp'].min()} → {df['timestamp'].max()})")
    return df


def _clean(record: dict) -> dict:
    """NaN -> None and pandas Timestamp -> datetime so both drivers accept the values."""
    out = {}
    for key, value in record.items():
        if isinstance(value, float) and math.isnan(value):
            value = None
        elif isinstance(value, pd.Timestamp):
            value = value.to_pydatetime()
        out[key] = value
    return out


def load_sql(df: pd.DataFrame, reset: bool) -> None:
    print(f"\n[SQL] {engine.url.render_as_string(hide_password=True)}")
    init_db()
    with SessionLocal() as session:
        if reset:
            session.query(Reading).delete()
            session.commit()

        for row in POLLUTANTS:
            if not session.query(PollutantReference).filter_by(code=row[0]).first():
                session.add(PollutantReference(
                    code=row[0], full_name=row[1], unit=row[2],
                    who_annual_limit=row[3], who_24h_limit=row[4], description=row[5]))
        for name in sorted(df["station"].unique()):
            if not session.query(Station).filter_by(station_name=name).first():
                session.add(Station(station_name=name, city="Beijing"))
        session.commit()
        station_ids = {s.station_name: s.station_id for s in session.query(Station)}

        existing = session.query(Reading).count()
        if existing and not reset:
            print(f"[SQL] readings already has {existing:,} rows — skipping (use --reset to reload).")
            return

    rows = df.assign(station_id=df["station"].map(station_ids)).drop(columns="station")
    records = [_clean(r) for r in rows.to_dict("records")]
    t0 = time.time()
    with engine.begin() as conn:
        for i in range(0, len(records), BATCH):
            conn.execute(Reading.__table__.insert(), records[i:i + BATCH])
            print(f"[SQL] {min(i + BATCH, len(records)):>7,} / {len(records):,}", end="\r")
    print(f"\n[SQL] inserted {len(records):,} readings in {time.time() - t0:.1f}s")


def load_mongo(df: pd.DataFrame, reset: bool) -> None:
    safe_uri = re.sub(r"(://[^:/@]+:)[^@]+@", r"\1****@", config.MONGO_URI)
    print(f"\n[Mongo] {safe_uri} → {config.MONGO_DB_NAME}.{config.MONGO_COLLECTION}")
    client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=5000)
    collection = client[config.MONGO_DB_NAME][config.MONGO_COLLECTION]
    if reset:
        collection.delete_many({})
    existing = collection.estimated_document_count()
    if existing and not reset:
        print(f"[Mongo] collection already has {existing:,} documents — skipping (use --reset to reload).")
        return
    ensure_indexes(collection)

    docs = [to_document(_clean(r)) for r in df.to_dict("records")]
    t0 = time.time()
    for i in range(0, len(docs), BATCH):
        collection.insert_many(docs[i:i + BATCH], ordered=False)
        print(f"[Mongo] {min(i + BATCH, len(docs)):>7,} / {len(docs):,}", end="\r")
    print(f"\n[Mongo] inserted {len(docs):,} documents in {time.time() - t0:.1f}s")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", default="data/raw", help="folder containing the 12 station CSVs")
    parser.add_argument("--target", choices=["all", "sql", "mongo"], default="all")
    parser.add_argument("--stations", nargs="*", help="only load these stations (default: all 12)")
    parser.add_argument("--reset", action="store_true", help="delete existing readings before loading")
    args = parser.parse_args()

    df = load_csvs(args.data_dir, args.stations)
    if args.target in ("all", "sql"):
        load_sql(df, args.reset)
    if args.target in ("all", "mongo"):
        load_mongo(df, args.reset)


if __name__ == "__main__":
    main()
