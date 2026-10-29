# Beijing Air Quality — Time-Series ML Pipeline

Group formative: time-series preprocessing, SQL + MongoDB databases, a CRUD/time-series API, and a forecasting script, built on the [Beijing Multi-Site Air Quality dataset](https://www.kaggle.com/datasets/sid321axn/beijing-multisite-airquality-data-set) (12 stations, hourly, 2013-03-01 → 2017-02-28, 420,768 rows).

## Live API

The API is deployed on Render:

- **Base URL:** https://formative1mlpipeline.onrender.com
- **Interactive docs (Swagger):** https://formative1mlpipeline.onrender.com/docs

It is backed by hosted databases: Aiven MySQL (`/sql`) and MongoDB Atlas (`/mongo`), both loaded with the full dataset.

> **Note: Render free tier sleeps.** The service spins down after ~15 minutes without traffic. The first request after that can take **up to a minute** while it wakes up; later requests are fast. If a request times out, wait a moment and retry, or open the docs link once to wake it before a demo. Scripts calling the API should use a generous timeout (e.g. `timeout=90`).

| Task | Owner | Location |
|------|-------|----------|
| 1. Preprocessing, EDA, model | Kyla (Member 1) | `notebooks/` *(to add)* |
| 2. MySQL + MongoDB design | Nicole (Member 2) | `notebooks/`, `database/schema_mysql.sql` |
| 3. CRUD + time-series API | David (Member 3) | `api/`, `database/load_data.py`, `tests/` |
| 4. Prediction script | Musiime (Member 4) | *(to add)* |

## Project structure

```
api/
  main.py                 FastAPI app (mounts /sql and /mongo routers)
  config.py               settings from environment / .env
  schemas.py              shared request/response models
  sql_db.py               SQLAlchemy models for the Task 2 MySQL schema
  mongo_db.py             MongoDB collection access + flat <-> nested mapping
  routers/sql_readings.py
  routers/mongo_readings.py
database/
  schema_mysql.sql        Task 2 DDL (stations, readings, pollutant_reference)
  load_data.py            loads the 12 CSVs into MySQL and MongoDB
tests/test_api.py         endpoint tests for both backends (SQLite in-memory + mongomock)
```

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then set your MySQL user/password
```

1. Download the Kaggle archive and unzip the 12 CSVs into `data/raw/`.
2. Create the MySQL database: `mysql -u <user> -p < database/schema_mysql.sql`
3. Make sure MongoDB is running on `localhost:27017`.
4. Load the data into both databases (≈30 s):

```bash
python -m database.load_data --data-dir data/raw
```

Options: `--target sql|mongo`, `--stations Dongsi Tiantan`, `--reset` (wipe and reload).

> **Hosted databases:** our shared instances are Aiven MySQL (set `SQL_SSL=true`) and MongoDB Atlas (`mongodb+srv://…`). Both are already loaded, so teammates only need the connection strings in their own `.env` (ask the team, never commit them). For Atlas, your IP must also be allowed under Network Access.
>
> No MySQL server? Set `SQL_DATABASE_URL=sqlite:///./beijing_air_quality.db`. The SQLAlchemy code is the same for both.

## Running the API

```bash
uvicorn api.main:app --reload
```

Interactive docs (try every endpoint in the browser): http://127.0.0.1:8000/docs

### Deploying to Render

The live instance uses these settings (Render → New → Web Service):

| Setting | Value |
|---|---|
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn api.main:app --host 0.0.0.0 --port $PORT` |
| Environment | `SQL_DATABASE_URL`, `SQL_SSL=true`, `MONGO_URI`, `MONGO_DB_NAME`, `MONGO_COLLECTION`, `PYTHON_VERSION` |

Atlas must allow connections from `0.0.0.0/0` (Network Access), because Render's free tier has no fixed outbound IP.

## Endpoints

Both backends expose the same routes under `/sql` and `/mongo`, and accept/return the same flat JSON shape:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/{db}/readings` | Create a reading (409 if that station-hour already exists) |
| `GET` | `/{db}/readings?station=&limit=&offset=` | List readings, newest first |
| `GET` | `/{db}/readings/{id}` | Get one reading |
| `PUT` | `/{db}/readings/{id}` | Partial update: only the fields you send change |
| `DELETE` | `/{db}/readings/{id}` | Delete a reading |
| `GET` | `/{db}/readings/latest?station=` | **Latest record**, overall or for one station |
| `GET` | `/{db}/readings/range?start=&end=&station=&limit=` | **Records by date range** (inclusive, oldest first) |
| `GET` | `/{db}/stations` | List stations |

`{db}` is `sql` or `mongo`. Timestamps are ISO-8601 (`2016-01-01T00:00:00`). `id` is the `reading_id` for SQL and the `ObjectId` string for MongoDB. `limit` is capped at 5000.

Reading shape:

```json
{
  "id": "140256", "station": "Dongsi", "timestamp": "2017-02-28T23:00:00",
  "pm25": 30.0, "pm10": 71.0, "so2": 11.0, "no2": 87.0, "co": 1200.0, "o3": 4.0,
  "temp": 8.6, "pres": 1014.1, "dewp": -15.9, "rain": 0.0,
  "wind_direction": "NNE", "wind_speed": 1.3
}
```

In MongoDB, readings are stored with the nested `pollutants` / `weather` structure designed in Task 2. The API converts them to the flat shape so clients can treat both backends the same way.

### Examples

Against the live deployment (swap in `http://127.0.0.1:8000` when running locally):

```bash
API=https://formative1mlpipeline.onrender.com

curl "$API/sql/readings/latest?station=Dongsi"
curl "$API/mongo/readings/range?start=2016-01-01T00:00:00&end=2016-01-07T23:00:00&station=Dongsi"
curl -X POST "$API/mongo/readings" -H "Content-Type: application/json" \
     -d '{"station":"Dongsi","timestamp":"2017-03-01T00:00:00","pm25":28,"temp":7.9}'
curl -X PUT "$API/sql/readings/<id>" -H "Content-Type: application/json" -d '{"pm25":35}'
curl -X DELETE "$API/sql/readings/<id>"
```

### For Task 4 (prediction script)

Fetch data from the live API, allowing for the free-tier wake-up delay:

```python
import requests

API = "https://formative1mlpipeline.onrender.com"
resp = requests.get(f"{API}/sql/readings/latest", params={"station": "Dongsi"}, timeout=90)
resp.raise_for_status()
reading = resp.json()
```

The model from Task 1 uses the raw CSV column names. Map the API fields back before predicting:

| API field | Model feature |
|-----------|---------------|
| `pm25`, `pm10`, `so2`, `no2`, `co`, `o3` | `PM2.5`, `PM10`, `SO2`, `NO2`, `CO`, `O3` |
| `temp`, `pres`, `dewp`, `rain`, `wind_speed` | `TEMP`, `PRES`, `DEWP`, `RAIN`, `WSPM` |
| `timestamp` | derive `hour`, `month` |

## Tests

```bash
pytest -v
```

26 tests run every endpoint against both backends. They cover CRUD, latest record, date range, duplicates (409), validation (422), reversed date ranges (400), and invalid ObjectIds (400). The tests need no running database: they use in-memory SQLite and mongomock.
