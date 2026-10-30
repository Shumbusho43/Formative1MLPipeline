# Beijing Air Quality: Time-Series ML Pipeline

This is a group formative project using the Beijing Multi-Site Air Quality dataset to demonstrate time-series preprocessing, exploratory data analysis (EDA), machine learning, relational and non-relational databases, CRUD APIs, and next-hour PM2.5 prediction.

**Problem:** PM2.5 particles are among the most dangerous pollutants that wander deep into airways and are linked to cardiovascular and respiratory disease. They account for 8 million global premature deaths annually. Unfortunately, 99% of the world's population lives in areas that fail to meet strict World Health Organization (WHO) air quality guidelines of 5 µg/m³, including Beijing whose levels at every one of their 12 stations far exceed health guidelines averaging at 66–86 μg/m³. 
This made us venture into exploring if we can forecast the PM2.5. Perhaps a reliable short-term forecast lets residents, schools and health services act before a pollution spike, for example by limiting outdoor activity or issuing alerts.

**Research question:** 
Given the pollutant and weather readings at a monitoring station for the current hour, can we predict the PM2.5 concentration (μg/m³) for the next hour?

The dataset contains hourly air-quality measurements from 12 monitoring stations between March 1, 2013, and February 28, 2017, with 420,768 records.

## Live API

- **Base URL:** https://formative1mlpipeline.onrender.com
- **Interactive API documentation:** https://formative1mlpipeline.onrender.com/docs

The deployed API uses hosted Aiven MySQL (`/sql`) and MongoDB Atlas (`/mongo`).

**Render free-tier note:** The service may sleep after a period without traffic. The first request can take up to a minute to respond. If a request times out, retry it or open the API documentation first.

## Project responsibilities

| Task | Member | Responsibility | Main location |
|---|---|---|---|
| 1 | Kyla Ochweri | Data preprocessing, EDA, feature engineering, model experiments | `notebooks/Beijing_Air_Quality_Task1.ipynb` |
| 2 | Nicole Mbera | MySQL and MongoDB database design | `notebooks/Beijing_Air_Quality_Task2_querries.ipynb`, `database/schema_mysql.sql`, `database/erd.png` |
| 3 | David Shumbusho | CRUD and time-series API | `api/`, `database/load_data.py`, `tests/` |
| 4 | Frank Musiime | Prediction script and model integration | `prediction/predict.py`, `models/best_rf.joblib` |

## Project structure

```text
Formative1MLPipeline/
├── notebooks/
│   ├── Beijing_Air_Quality_Task1.ipynb          Task 1: EDA, analytical questions, model training
│   └── Beijing_Air_Quality_Task2_querries.ipynb Task 2: schema, ERD, SQL and MongoDB queries
├── database/
│   ├── schema_mysql.sql                         MySQL DDL (3 tables)
│   ├── erd.png                                  Entity-relationship diagram
│   └── load_data.py                             Loads the CSVs into MySQL and MongoDB
├── api/                                         Task 3: FastAPI service
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   ├── sql_db.py
│   ├── mongo_db.py
│   └── routers/
│       ├── sql_readings.py
│       └── mongo_readings.py
├── prediction/
│   └── predict.py                               Task 4: API → model → forecast
├── models/
│   └── best_rf.joblib                           Tuned Random Forest pipeline
├── tests/
│   ├── conftest.py                              Keeps tests off the hosted databases
│   ├── test_api.py
│   └── test_prediction.py
├── report/
│   ├── Group_Report.pdf
│   └── Group_Report.docx
├── data/raw/                                    Kaggle CSVs (not committed, see Setup)
├── requirements.txt
├── .env.example                                 Settings to copy into .env (not committed)
└── README.md
```

## 1. Setup

### Prerequisites

- Python version compatible with `requirements.txt`
- Access to a configured MySQL database
- Access to a configured MongoDB database
- Dataset files for local data loading, if required

### Install dependencies

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Configure database environment variables using `.env.example` as a reference. Keep credentials and connection strings in `.env`, and never commit secrets to Git.

### Dataset and database setup

1. Download the [Beijing Multi-Site Air Quality dataset from Kaggle](https://www.kaggle.com/datasets/sid321axn/beijing-multisite-airquality-data-set).
2. Extract the station CSV files into `data/raw/` if using the local data loader.
3. Configure the SQL and MongoDB connection settings.
4. Apply the MySQL schema and load the data using the instructions supported by the current loader.

Check the loader's actual options before using it:

```bash
python -m database.load_data --help
```

The deployed API uses hosted databases. Local setup may require separate database configuration and data loading.

## 2. Task 1 — Time-series analysis and machine learning

The Task 1 notebook is `notebooks/Beijing_Air_Quality_Task1.ipynb`. It is written for Google Colab: the first cell asks you to upload the Kaggle ZIP archive, which it extracts to `/content/beijing_air_quality`.

The model predicts **next-hour PM2.5 concentration for the Dongsi station**. The target is formed by shifting the PM2.5 series by one hour, while the input features represent the current observation and time.

The 13 model features are:

| Feature group | Features |
|---|---|
| Pollutants | `PM2.5`, `PM10`, `SO2`, `NO2`, `CO`, `O3` |
| Weather | `TEMP`, `PRES`, `DEWP`, `RAIN`, `WSPM` |
| Time | `hour`, `month` |

Reported model results:

| Model | MAE | RMSE | R² |
|---|---:|---:|---:|
| Baseline Random Forest | 11.558 | 22.164 | 0.942 |
| Tuned Random Forest | 11.146 | 21.615 | 0.945 |

The tuned model used randomized hyperparameter search with time-series cross-validation. The saved pipeline is `models/best_rf.joblib`.

Ensure the notebook includes the assignment's required analytical questions, visualizations, interpretations, lagged features, moving averages, and experiment comparisons.

## 3. Task 2 — Relational and non-relational databases

The Task 2 notebook is `notebooks/Beijing_Air_Quality_Task2_querries.ipynb`. It connects to the hosted databases (Aiven MySQL and MongoDB Atlas) using the settings in `.env`, verifies that all 420,768 records are present, and runs 5 SQL and 4 MongoDB queries with their results saved in the notebook. It can be run from the project root or from `notebooks/`, with the CSVs in `data/raw/`.

### MySQL

The MySQL schema is in `database/schema_mysql.sql` and the ERD is `database/erd.png`. The tables are:

- `stations`
- `readings`
- `pollutant_reference`

### MongoDB

The `air_quality_readings` collection stores one document per station-hour, with nested `pollutants` and `weather` sub-documents. The API maps documents into the same flat response shape as the SQL endpoints.

## 4. Task 3 — CRUD and time-series API

The API uses FastAPI and exposes endpoints for SQL and MongoDB.

Start the API locally from the project root:

```bash
python -m uvicorn api.main:app --reload
```

Open the interactive documentation at:

http://127.0.0.1:8000/docs

### Endpoint summary

Both database backends use the `/sql` and `/mongo` prefixes.

| Method | Path | Description |
|---|---|---|
| `POST` | `/{db}/readings` | Create a reading |
| `GET` | `/{db}/readings` | List readings, with optional filtering and pagination |
| `GET` | `/{db}/readings/{id}` | Retrieve a reading by ID |
| `PUT` | `/{db}/readings/{id}` | Update a reading |
| `DELETE` | `/{db}/readings/{id}` | Delete a reading |
| `GET` | `/{db}/readings/latest?station=Dongsi` | Retrieve the latest reading |
| `GET` | `/{db}/readings/range?start=...&end=...` | Retrieve readings in a date range |
| `GET` | `/{db}/stations` | List stations |

Here, `{db}` is either `sql` or `mongo`.

The API supports reading creation, retrieval, updates, deletion, latest-record retrieval, and date-range queries. Consult the live Swagger documentation for the exact request schemas and available parameters.

### Example requests

```bash
API="https://formative1mlpipeline.onrender.com"

curl "$API/sql/readings/latest?station=Dongsi"
curl "$API/mongo/readings/latest?station=Dongsi"
```

For local testing, replace the base URL with `http://127.0.0.1:8000`.

Use suitable test records when demonstrating create, update, and delete operations. Do not assume example IDs exist in the database.

## 5. Task 4 — Prediction script and model integration

The script `prediction/predict.py` connects the API to the saved model.

It:

1. Loads `models/best_rf.joblib`.
2. Fetches the latest available reading for the selected station from the API.
3. Maps API field names to the model's training feature names.
4. Derives `hour` and `month` from the timestamp.
5. Predicts next-hour PM2.5 concentration.

Run the script from the project root:

```powershell
python prediction/predict.py
```

The script expects the API to be available at the URL configured in the script. For local testing, the API should be running in another terminal. The deployed API may require a longer HTTP timeout because the free service can sleep.

### Feature mapping

| API field | Model feature |
|---|---|
| `pm25` | `PM2.5` |
| `pm10` | `PM10` |
| `so2` | `SO2` |
| `no2` | `NO2` |
| `co` | `CO` |
| `o3` | `O3` |
| `temp` | `TEMP` |
| `pres` | `PRES` |
| `dewp` | `DEWP` |
| `rain` | `RAIN` |
| `wind_speed` | `WSPM` |
| `timestamp` | Derive `hour` and `month` |

The feature names and order must match those used during training. The script should load the complete saved pipeline, including its preprocessing steps.

### Example output

A previous successful run produced:

<img width="550" height="112" alt="image" src="https://github.com/user-attachments/assets/947ce026-49f4-42df-8598-221cc26ebfa8" />

This is a prediction based on the latest available record in the historical dataset, which ends on February 28, 2017. It is **not a forecast of current air quality**.

## 6. Testing

Run the tests from the project root:

```bash
python -m pytest -v
```

The latest reported test run completed with **31 passed tests**:

- 26 API tests covering SQL and MongoDB API behavior.
- 5 prediction tests covering feature preparation, prediction output, missing fields, invalid timestamps, and HTTP error handling.

The API tests use test database substitutes, including in-memory SQLite and `mongomock`. A passing test suite does not replace verification of the deployed database configuration or an end-to-end demonstration.

## 7. Limitations

- The dataset ends in February 2017.
- The prediction script uses the latest available record from the configured API.
- The model predicts next-hour PM2.5 for Dongsi; performance should not be assumed to generalize to all stations without further evaluation.
- Model performance metrics describe the evaluated data split and do not guarantee future accuracy.
- Database credentials and API secrets must remain private.

