"""SQLAlchemy models mirroring the Task 2 MySQL schema (stations, readings, pollutant_reference)."""
from datetime import datetime

from sqlalchemy import (
    BigInteger, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint, create_engine, func,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from api import config

Base = declarative_base()

# BIGINT on MySQL, INTEGER on SQLite (SQLite only auto-increments INTEGER PRIMARY KEY).
BigIntId = BigInteger().with_variant(Integer(), "sqlite")


class Station(Base):
    __tablename__ = "stations"

    station_id = Column(Integer, primary_key=True, autoincrement=True)
    station_name = Column(String(50), nullable=False, unique=True)
    city = Column(String(100), nullable=False, default="Beijing")
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    readings = relationship("Reading", back_populates="station")


class Reading(Base):
    __tablename__ = "readings"
    __table_args__ = (
        UniqueConstraint("station_id", "timestamp", name="uq_station_ts"),
        Index("idx_timestamp", "timestamp"),
        Index("idx_station_ts", "station_id", "timestamp"),
    )

    reading_id = Column(BigIntId, primary_key=True, autoincrement=True)
    station_id = Column(
        Integer,
        ForeignKey("stations.station_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    timestamp = Column(DateTime, nullable=False)
    pm25 = Column(Float)
    pm10 = Column(Float)
    so2 = Column(Float)
    no2 = Column(Float)
    co = Column(Float)
    o3 = Column(Float)
    temp = Column(Float)
    pres = Column(Float)
    dewp = Column(Float)
    rain = Column(Float)
    wind_direction = Column(String(10))
    wind_speed = Column(Float)

    station = relationship("Station", back_populates="readings")


class PollutantReference(Base):
    __tablename__ = "pollutant_reference"

    pollutant_id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), nullable=False, unique=True)
    full_name = Column(String(100), nullable=False)
    unit = Column(String(20), nullable=False)
    who_annual_limit = Column(Float)
    who_24h_limit = Column(Float)
    description = Column(Text)


def make_engine(url: str = config.SQL_DATABASE_URL):
    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    elif config.SQL_SSL:
        # Without a CA file PyMySQL encrypts but skips certificate checks (ssl-mode=REQUIRED).
        ssl = {"ca": config.SQL_SSL_CA} if config.SQL_SSL_CA else {"check_hostname": False}
        kwargs["connect_args"] = {"ssl": ssl}
        kwargs["pool_recycle"] = 280  # hosted servers drop idle connections
    return create_engine(url, **kwargs)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db(bind=None) -> None:
    """Create the tables if they do not exist yet."""
    Base.metadata.create_all(bind=bind or engine)


def get_session():
    """FastAPI dependency: one session per request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def reading_to_dict(reading: Reading) -> dict:
    """Flatten a Reading row into the shared API representation."""
    return {
        "id": str(reading.reading_id),
        "station": reading.station.station_name,
        "timestamp": reading.timestamp,
        "pm25": reading.pm25,
        "pm10": reading.pm10,
        "so2": reading.so2,
        "no2": reading.no2,
        "co": reading.co,
        "o3": reading.o3,
        "temp": reading.temp,
        "pres": reading.pres,
        "dewp": reading.dewp,
        "rain": reading.rain,
        "wind_direction": reading.wind_direction,
        "wind_speed": reading.wind_speed,
    }


def get_or_create_station(session, name: str) -> Station:
    station = session.query(Station).filter(Station.station_name == name).one_or_none()
    if station is None:
        station = Station(station_name=name, city="Beijing", created_at=datetime.utcnow())
        session.add(station)
        session.flush()
    return station
