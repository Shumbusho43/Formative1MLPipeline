"""Pydantic request/response models shared by the SQL and MongoDB endpoints."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Measurements(BaseModel):
    """Pollutant (μg/m³) and weather values for one station-hour. All optional: the raw data has gaps."""
    pm25: Optional[float] = Field(None, ge=0, description="PM2.5 concentration (μg/m³)")
    pm10: Optional[float] = Field(None, ge=0, description="PM10 concentration (μg/m³)")
    so2: Optional[float] = Field(None, ge=0, description="SO2 concentration (μg/m³)")
    no2: Optional[float] = Field(None, ge=0, description="NO2 concentration (μg/m³)")
    co: Optional[float] = Field(None, ge=0, description="CO concentration (μg/m³)")
    o3: Optional[float] = Field(None, ge=0, description="O3 concentration (μg/m³)")
    temp: Optional[float] = Field(None, description="Temperature (°C)")
    pres: Optional[float] = Field(None, description="Air pressure (hPa)")
    dewp: Optional[float] = Field(None, description="Dew-point temperature (°C)")
    rain: Optional[float] = Field(None, ge=0, description="Precipitation (mm)")
    wind_direction: Optional[str] = Field(None, max_length=10, description="Compass direction, e.g. NNW")
    wind_speed: Optional[float] = Field(None, ge=0, description="Wind speed (m/s)")


class ReadingCreate(Measurements):
    station: str = Field(..., min_length=1, max_length=50, examples=["Dongsi"])
    timestamp: datetime = Field(..., examples=["2017-03-01T00:00:00"])

    model_config = ConfigDict(json_schema_extra={"example": {
        "station": "Dongsi", "timestamp": "2017-03-01T00:00:00",
        "pm25": 28.0, "pm10": 60.0, "so2": 10.0, "no2": 80.0, "co": 1100.0, "o3": 5.0,
        "temp": 7.9, "pres": 1014.5, "dewp": -15.2, "rain": 0.0,
        "wind_direction": "NNE", "wind_speed": 1.4,
    }})


class ReadingUpdate(Measurements):
    """PUT body: only the fields provided are changed."""
    station: Optional[str] = Field(None, min_length=1, max_length=50)
    timestamp: Optional[datetime] = None

    model_config = ConfigDict(json_schema_extra={"example": {"pm25": 35.0, "temp": 8.2}})


class ReadingOut(ReadingCreate):
    id: str = Field(..., description="reading_id (SQL) or ObjectId (MongoDB)")


class ReadingList(BaseModel):
    count: int
    items: List[ReadingOut]


class Message(BaseModel):
    detail: str
