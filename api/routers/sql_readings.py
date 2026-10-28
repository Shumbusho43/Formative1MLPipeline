"""CRUD + time-series endpoints backed by the relational (MySQL) database."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from api import config
from api.schemas import Message, ReadingCreate, ReadingList, ReadingOut, ReadingUpdate
from api.sql_db import Reading, Station, get_or_create_station, get_session, reading_to_dict

router = APIRouter(prefix="/sql", tags=["SQL (MySQL)"])

DUPLICATE = "A reading for this station and timestamp already exists."


def _base_query(session: Session, station: Optional[str]):
    query = session.query(Reading).options(joinedload(Reading.station))
    if station:
        query = query.join(Station).filter(Station.station_name == station)
    return query


def _get_or_404(session: Session, reading_id: int) -> Reading:
    reading = _base_query(session, None).filter(Reading.reading_id == reading_id).one_or_none()
    if reading is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Reading {reading_id} not found.")
    return reading


@router.get("/stations", summary="List monitoring stations")
def list_stations(session: Session = Depends(get_session)):
    stations = session.query(Station).order_by(Station.station_name).all()
    return [{"station_id": s.station_id, "station_name": s.station_name, "city": s.city}
            for s in stations]


# ── Time-series queries (declared before /readings/{id} so the paths don't collide) ──

@router.get("/readings/latest", response_model=ReadingOut,
            responses={404: {"model": Message}}, summary="Latest record")
def latest_reading(station: Optional[str] = Query(None, examples=["Dongsi"]),
                   session: Session = Depends(get_session)):
    """Most recent reading, optionally for a single station."""
    reading = (_base_query(session, station)
               .order_by(Reading.timestamp.desc(), Reading.reading_id.desc())
               .first())
    if reading is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No readings found.")
    return reading_to_dict(reading)


@router.get("/readings/range", response_model=ReadingList,
            responses={400: {"model": Message}}, summary="Records by date range")
def readings_in_range(start: datetime = Query(..., examples=["2016-01-01T00:00:00"]),
                      end: datetime = Query(..., examples=["2016-01-07T23:00:00"]),
                      station: Optional[str] = Query(None, examples=["Dongsi"]),
                      limit: int = Query(1000, ge=1, le=config.MAX_PAGE_SIZE),
                      session: Session = Depends(get_session)):
    """Readings with `start <= timestamp <= end`, oldest first."""
    if start > end:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "`start` must be before `end`.")
    readings = (_base_query(session, station)
                .filter(Reading.timestamp >= start, Reading.timestamp <= end)
                .order_by(Reading.timestamp, Reading.station_id)
                .limit(limit)
                .all())
    return {"count": len(readings), "items": [reading_to_dict(r) for r in readings]}


# ── CRUD ─────────────────────────────────────────────────────────────────────

@router.post("/readings", response_model=ReadingOut, status_code=status.HTTP_201_CREATED,
             responses={409: {"model": Message}}, summary="Create a reading")
def create_reading(payload: ReadingCreate, session: Session = Depends(get_session)):
    data = payload.model_dump()
    station = get_or_create_station(session, data.pop("station"))
    reading = Reading(station_id=station.station_id, **data)
    session.add(reading)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, DUPLICATE)
    return reading_to_dict(_get_or_404(session, reading.reading_id))


@router.get("/readings", response_model=ReadingList, summary="List readings")
def list_readings(station: Optional[str] = None,
                  limit: int = Query(100, ge=1, le=config.MAX_PAGE_SIZE),
                  offset: int = Query(0, ge=0),
                  session: Session = Depends(get_session)):
    readings = (_base_query(session, station)
                .order_by(Reading.timestamp.desc(), Reading.reading_id.desc())
                .offset(offset).limit(limit).all())
    return {"count": len(readings), "items": [reading_to_dict(r) for r in readings]}


@router.get("/readings/{reading_id}", response_model=ReadingOut,
            responses={404: {"model": Message}}, summary="Get a reading by id")
def get_reading(reading_id: int, session: Session = Depends(get_session)):
    return reading_to_dict(_get_or_404(session, reading_id))


@router.put("/readings/{reading_id}", response_model=ReadingOut,
            responses={404: {"model": Message}, 409: {"model": Message}},
            summary="Update a reading")
def update_reading(reading_id: int, payload: ReadingUpdate,
                   session: Session = Depends(get_session)):
    reading = _get_or_404(session, reading_id)
    changes = payload.model_dump(exclude_unset=True)
    if "station" in changes:
        reading.station = get_or_create_station(session, changes.pop("station"))
    for field, value in changes.items():
        setattr(reading, field, value)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, DUPLICATE)
    return reading_to_dict(_get_or_404(session, reading_id))


@router.delete("/readings/{reading_id}", response_model=Message,
               responses={404: {"model": Message}}, summary="Delete a reading")
def delete_reading(reading_id: int, session: Session = Depends(get_session)):
    session.delete(_get_or_404(session, reading_id))
    session.commit()
    return {"detail": f"Reading {reading_id} deleted."}
