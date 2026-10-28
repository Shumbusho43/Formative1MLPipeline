"""MongoDB access for the Task 2 `air_quality_readings` collection.

Documents are stored nested (pollutants / weather sub-documents, as designed in
Task 2) but exposed through the API in the same flat shape as the SQL endpoints.
"""
from typing import Optional

from pymongo import ASCENDING, DESCENDING, MongoClient

from api import config

# API field  ->  path inside the Mongo document
FIELD_MAP = {
    "pm25": "pollutants.pm25",
    "pm10": "pollutants.pm10",
    "so2": "pollutants.so2",
    "no2": "pollutants.no2",
    "co": "pollutants.co",
    "o3": "pollutants.o3",
    "temp": "weather.temp",
    "pres": "weather.pressure",
    "dewp": "weather.dew_point",
    "rain": "weather.rainfall",
    "wind_direction": "weather.wind_direction",
    "wind_speed": "weather.wind_speed",
}

_collection = None


def get_collection():
    """Return the readings collection, connecting lazily on first use."""
    global _collection
    if _collection is None:
        client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=5000, tz_aware=False)
        set_collection(client[config.MONGO_DB_NAME][config.MONGO_COLLECTION])
    return _collection


def set_collection(collection) -> None:
    """Swap the collection (used by tests to inject mongomock)."""
    global _collection
    _collection = collection
    ensure_indexes(collection)


def ensure_indexes(collection) -> None:
    """Indexes recommended in Task 2: (station, timestamp) unique, timestamp, pm25."""
    collection.create_index([("station", ASCENDING), ("timestamp", ASCENDING)],
                            unique=True, name="station_timestamp")
    collection.create_index([("timestamp", DESCENDING)], name="timestamp")
    collection.create_index([("pollutants.pm25", ASCENDING)], name="pm25")


def to_document(data: dict) -> dict:
    """Flat API payload -> nested Task 2 document."""
    ts = data["timestamp"]
    doc = {
        "station": data["station"],
        "timestamp": ts,
        "year": ts.year, "month": ts.month, "day": ts.day, "hour": ts.hour,
        "pollutants": {},
        "weather": {},
    }
    for field, path in FIELD_MAP.items():
        group, key = path.split(".")
        doc[group][key] = data.get(field)
    return doc


def to_update(data: dict) -> dict:
    """Partial flat payload -> `$set` spec using dotted paths."""
    update = {}
    for field, value in data.items():
        if field in FIELD_MAP:
            update[FIELD_MAP[field]] = value
        elif field == "timestamp":
            update.update({"timestamp": value, "year": value.year, "month": value.month,
                           "day": value.day, "hour": value.hour})
        else:
            update[field] = value
    return update


def from_document(doc: dict) -> dict:
    """Nested Task 2 document -> flat API representation."""
    out = {"id": str(doc["_id"]), "station": doc["station"], "timestamp": doc["timestamp"]}
    for field, path in FIELD_MAP.items():
        group, key = path.split(".")
        out[field] = (doc.get(group) or {}).get(key)
    return out


def station_filter(station: Optional[str]) -> dict:
    return {"station": station} if station else {}
