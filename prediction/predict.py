
from pathlib import Path

import joblib
import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "best_rf.joblib"

API_URL = "http://127.0.0.1:8000/sql/readings/latest"
DEFAULT_STATION = "Dongsi"

FEATURE_COLUMNS = [
    "PM2.5",
    "PM10",
    "SO2",
    "NO2",
    "CO",
    "O3",
    "TEMP",
    "PRES",
    "DEWP",
    "RAIN",
    "WSPM",
    "hour",
    "month",
]


def load_model():
    """Load the trained machine-learning pipeline."""
    return joblib.load(MODEL_PATH)


def fetch_latest_reading(station=DEFAULT_STATION):
    """Fetch the latest reading for a station from the API."""
    response = requests.get(
        API_URL,
        params={"station": station},
        timeout=30,
    )
    response.raise_for_status()

    return response.json()


def prepare_features(reading):
    """Convert an API reading into the model's expected features."""
    timestamp = pd.to_datetime(reading["timestamp"])

    features = pd.DataFrame([{
        "PM2.5": reading["pm25"],
        "PM10": reading["pm10"],
        "SO2": reading["so2"],
        "NO2": reading["no2"],
        "CO": reading["co"],
        "O3": reading["o3"],
        "TEMP": reading["temp"],
        "PRES": reading["pres"],
        "DEWP": reading["dewp"],
        "RAIN": reading["rain"],
        "WSPM": reading["wind_speed"],
        "hour": timestamp.hour,
        "month": timestamp.month,
    }])

    return features[FEATURE_COLUMNS]


def predict_next_hour(model, reading):
    """Predict the next-hour PM2.5 value from a reading."""
    features = prepare_features(reading)
    prediction = model.predict(features)[0]

    return float(prediction)


def main():
    """Fetch a reading and print the model's prediction."""
    model = load_model()
    reading = fetch_latest_reading()
    prediction = predict_next_hour(model, reading)

    print(f"Station: {reading['station']}")
    print(f"Latest recorded timestamp: {reading['timestamp']}")
    print(f"Latest recorded PM2.5: {reading['pm25']}")
    print(f"Predicted next-hour PM2.5: {prediction:.2f}")


if __name__ == "__main__":
    main()
