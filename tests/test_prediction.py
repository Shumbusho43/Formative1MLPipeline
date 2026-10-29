import pytest
import requests

from prediction.predict import (
    FEATURE_COLUMNS,
    fetch_latest_reading,
    predict_next_hour,
    prepare_features,
)


def test_fetch_latest_reading_http_error(monkeypatch):
    """Check that an unsuccessful API response raises an HTTP error."""

    def fake_get(*args, **kwargs):
        response = requests.Response()
        response.status_code = 500
        return response

    monkeypatch.setattr("prediction.predict.requests.get", fake_get)

    with pytest.raises(requests.HTTPError):
        fetch_latest_reading()


def sample_reading():
    """Return a sample API reading for testing."""
    return {
        "station": "Dongsi",
        "timestamp": "2017-02-28T23:00:00",
        "pm25": 30.0,
        "pm10": 71.0,
        "so2": 11.0,
        "no2": 87.0,
        "co": 1200.0,
        "o3": 4.0,
        "temp": 8.6,
        "pres": 1014.1,
        "dewp": -15.9,
        "rain": 0.0,
        "wind_speed": 1.3,
    }


class FakeModel:
    """Simulate a model that predicts PM2.5 as 40.68."""

    def predict(self, features):
        """Return a fixed prediction for testing."""
        assert list(features.columns) == FEATURE_COLUMNS
        assert len(features) == 1
        return [40.68]


def test_prepare_features():
    """Check feature names, order, and timestamp-derived values."""
    reading = sample_reading()

    features = prepare_features(reading)

    assert list(features.columns) == FEATURE_COLUMNS
    assert features.shape == (1, 13)
    assert features.iloc[0]["PM2.5"] == 30.0
    assert features.iloc[0]["hour"] == 23
    assert features.iloc[0]["month"] == 2


def test_predict_next_hour():
    """Check that the model prediction is returned as a float."""
    model = FakeModel()
    reading = sample_reading()

    prediction = predict_next_hour(model, reading)

    assert prediction == 40.68
    assert isinstance(prediction, float)


def test_prepare_features_missing_field():
    """Check that a missing required field raises an error."""
    reading = sample_reading()
    del reading["pm25"]

    with pytest.raises(KeyError):
        prepare_features(reading)


def test_prepare_features_invalid_timestamp():
    """Check that an invalid timestamp raises an error."""
    reading = sample_reading()
    reading["timestamp"] = "not-a-valid-timestamp"

    with pytest.raises((ValueError, TypeError)):
        prepare_features(reading)
