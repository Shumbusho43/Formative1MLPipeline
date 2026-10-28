"""API tests for both backends: an in-memory SQLite database and mongomock.

Run:  pytest -v
"""
import mongomock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from api import mongo_db
from api.main import app
from api.sql_db import Base, get_session

BACKENDS = ["sql", "mongo"]

READING = {
    "station": "Dongsi", "timestamp": "2017-02-28T23:00:00",
    "pm25": 30.0, "pm10": 71.0, "so2": 11.0, "no2": 87.0, "co": 1200.0, "o3": 4.0,
    "temp": 8.6, "pres": 1014.1, "dewp": -15.9, "rain": 0.0,
    "wind_direction": "NNE", "wind_speed": 1.3,
}


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_session():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_session
    mongo_db.set_collection(mongomock.MongoClient()["test"]["air_quality_readings"])
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def seed(client, backend):
    """Insert 3 hours at Dongsi plus 1 at Tiantan; return the created records."""
    created = []
    for station, ts, pm25 in [("Dongsi", "2016-01-01T00:00:00", 200.0),
                              ("Dongsi", "2016-01-01T01:00:00", 193.0),
                              ("Dongsi", "2016-01-01T02:00:00", 219.0),
                              ("Tiantan", "2016-01-01T03:00:00", 150.0)]:
        res = client.post(f"/{backend}/readings",
                          json={**READING, "station": station, "timestamp": ts, "pm25": pm25})
        assert res.status_code == 201, res.text
        created.append(res.json())
    return created


@pytest.mark.parametrize("backend", BACKENDS)
def test_create_and_get(client, backend):
    res = client.post(f"/{backend}/readings", json=READING)
    assert res.status_code == 201
    body = res.json()
    assert body["station"] == "Dongsi" and body["pm25"] == 30.0 and body["id"]

    fetched = client.get(f"/{backend}/readings/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


@pytest.mark.parametrize("backend", BACKENDS)
def test_duplicate_station_hour_rejected(client, backend):
    assert client.post(f"/{backend}/readings", json=READING).status_code == 201
    assert client.post(f"/{backend}/readings", json=READING).status_code == 409


@pytest.mark.parametrize("backend", BACKENDS)
def test_validation_error(client, backend):
    res = client.post(f"/{backend}/readings", json={**READING, "pm25": -5})
    assert res.status_code == 422


@pytest.mark.parametrize("backend", BACKENDS)
def test_list_with_station_filter(client, backend):
    seed(client, backend)
    body = client.get(f"/{backend}/readings", params={"station": "Dongsi"}).json()
    assert body["count"] == 3
    assert all(r["station"] == "Dongsi" for r in body["items"])
    # newest first
    assert body["items"][0]["timestamp"] == "2016-01-01T02:00:00"


@pytest.mark.parametrize("backend", BACKENDS)
def test_update(client, backend):
    record = seed(client, backend)[0]
    res = client.put(f"/{backend}/readings/{record['id']}", json={"pm25": 55.5, "temp": -1.0})
    assert res.status_code == 200
    body = res.json()
    assert body["pm25"] == 55.5 and body["temp"] == -1.0
    assert body["pm10"] == record["pm10"]  # untouched fields are preserved


@pytest.mark.parametrize("backend", BACKENDS)
def test_update_into_duplicate_rejected(client, backend):
    first, second = seed(client, backend)[:2]
    res = client.put(f"/{backend}/readings/{second['id']}", json={"timestamp": first["timestamp"]})
    assert res.status_code == 409


@pytest.mark.parametrize("backend", BACKENDS)
def test_delete(client, backend):
    record = seed(client, backend)[0]
    assert client.delete(f"/{backend}/readings/{record['id']}").status_code == 200
    assert client.get(f"/{backend}/readings/{record['id']}").status_code == 404
    assert client.delete(f"/{backend}/readings/{record['id']}").status_code == 404


@pytest.mark.parametrize("backend", BACKENDS)
def test_latest(client, backend):
    seed(client, backend)
    overall = client.get(f"/{backend}/readings/latest").json()
    assert overall["station"] == "Tiantan" and overall["timestamp"] == "2016-01-01T03:00:00"

    dongsi = client.get(f"/{backend}/readings/latest", params={"station": "Dongsi"}).json()
    assert dongsi["timestamp"] == "2016-01-01T02:00:00" and dongsi["pm25"] == 219.0


@pytest.mark.parametrize("backend", BACKENDS)
def test_latest_empty(client, backend):
    assert client.get(f"/{backend}/readings/latest").status_code == 404


@pytest.mark.parametrize("backend", BACKENDS)
def test_date_range(client, backend):
    seed(client, backend)
    params = {"start": "2016-01-01T01:00:00", "end": "2016-01-01T03:00:00"}
    body = client.get(f"/{backend}/readings/range", params=params).json()
    assert [r["timestamp"] for r in body["items"]] == [
        "2016-01-01T01:00:00", "2016-01-01T02:00:00", "2016-01-01T03:00:00"]

    body = client.get(f"/{backend}/readings/range", params={**params, "station": "Dongsi"}).json()
    assert body["count"] == 2

    body = client.get(f"/{backend}/readings/range", params={**params, "limit": 1}).json()
    assert body["count"] == 1


@pytest.mark.parametrize("backend", BACKENDS)
def test_date_range_rejects_reversed_dates(client, backend):
    res = client.get(f"/{backend}/readings/range",
                     params={"start": "2016-02-01T00:00:00", "end": "2016-01-01T00:00:00"})
    assert res.status_code == 400


@pytest.mark.parametrize("backend", BACKENDS)
def test_stations(client, backend):
    seed(client, backend)
    body = client.get(f"/{backend}/stations").json()
    names = [s["station_name"] for s in body] if backend == "sql" else body
    assert names == ["Dongsi", "Tiantan"]


def test_mongo_invalid_object_id(client):
    assert client.get("/mongo/readings/not-an-id").status_code == 400


def test_mongo_document_is_nested(client):
    """The API is flat, but storage follows the Task 2 nested document design."""
    client.post("/mongo/readings", json=READING)
    doc = mongo_db.get_collection().find_one({"station": "Dongsi"})
    assert doc["pollutants"]["pm25"] == 30.0
    assert doc["weather"]["pressure"] == 1014.1
    assert (doc["year"], doc["month"], doc["day"], doc["hour"]) == (2017, 2, 28, 23)
