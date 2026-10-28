"""CRUD + time-series endpoints backed by MongoDB (`air_quality_readings` collection)."""
from datetime import datetime
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query, status
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from api import config
from api.mongo_db import from_document, get_collection, station_filter, to_document, to_update
from api.schemas import Message, ReadingCreate, ReadingList, ReadingOut, ReadingUpdate

router = APIRouter(prefix="/mongo", tags=["MongoDB"])

DUPLICATE = "A reading for this station and timestamp already exists."


def _object_id(reading_id: str) -> ObjectId:
    try:
        return ObjectId(reading_id)
    except (InvalidId, TypeError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"'{reading_id}' is not a valid ObjectId.")


def _get_or_404(reading_id: str) -> dict:
    doc = get_collection().find_one({"_id": _object_id(reading_id)})
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Reading {reading_id} not found.")
    return doc


@router.get("/stations", summary="List monitoring stations")
def list_stations():
    return sorted(get_collection().distinct("station"))


# ── Time-series queries (declared before /readings/{id} so the paths don't collide) ──

@router.get("/readings/latest", response_model=ReadingOut,
            responses={404: {"model": Message}}, summary="Latest record")
def latest_reading(station: Optional[str] = Query(None, examples=["Dongsi"])):
    """Most recent reading, optionally for a single station."""
    docs = list(get_collection().find(station_filter(station))
                .sort([("timestamp", -1), ("_id", -1)]).limit(1))
    if not docs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No readings found.")
    return from_document(docs[0])


@router.get("/readings/range", response_model=ReadingList,
            responses={400: {"model": Message}}, summary="Records by date range")
def readings_in_range(start: datetime = Query(..., examples=["2016-01-01T00:00:00"]),
                      end: datetime = Query(..., examples=["2016-01-07T23:00:00"]),
                      station: Optional[str] = Query(None, examples=["Dongsi"]),
                      limit: int = Query(1000, ge=1, le=config.MAX_PAGE_SIZE)):
    """Readings with `start <= timestamp <= end`, oldest first."""
    if start > end:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "`start` must be before `end`.")
    query = {**station_filter(station), "timestamp": {"$gte": start, "$lte": end}}
    docs = list(get_collection().find(query)
                .sort([("timestamp", 1), ("station", 1)]).limit(limit))
    return {"count": len(docs), "items": [from_document(d) for d in docs]}


# ── CRUD ─────────────────────────────────────────────────────────────────────

@router.post("/readings", response_model=ReadingOut, status_code=status.HTTP_201_CREATED,
             responses={409: {"model": Message}}, summary="Create a reading")
def create_reading(payload: ReadingCreate):
    doc = to_document(payload.model_dump())
    try:
        result = get_collection().insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(status.HTTP_409_CONFLICT, DUPLICATE)
    doc["_id"] = result.inserted_id
    return from_document(doc)


@router.get("/readings", response_model=ReadingList, summary="List readings")
def list_readings(station: Optional[str] = None,
                  limit: int = Query(100, ge=1, le=config.MAX_PAGE_SIZE),
                  offset: int = Query(0, ge=0)):
    docs = list(get_collection().find(station_filter(station))
                .sort([("timestamp", -1), ("_id", -1)]).skip(offset).limit(limit))
    return {"count": len(docs), "items": [from_document(d) for d in docs]}


@router.get("/readings/{reading_id}", response_model=ReadingOut,
            responses={400: {"model": Message}, 404: {"model": Message}},
            summary="Get a reading by id")
def get_reading(reading_id: str):
    return from_document(_get_or_404(reading_id))


@router.put("/readings/{reading_id}", response_model=ReadingOut,
            responses={400: {"model": Message}, 404: {"model": Message}, 409: {"model": Message}},
            summary="Update a reading")
def update_reading(reading_id: str, payload: ReadingUpdate):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return from_document(_get_or_404(reading_id))
    try:
        doc = get_collection().find_one_and_update(
            {"_id": _object_id(reading_id)},
            {"$set": to_update(changes)},
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError:
        raise HTTPException(status.HTTP_409_CONFLICT, DUPLICATE)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Reading {reading_id} not found.")
    return from_document(doc)


@router.delete("/readings/{reading_id}", response_model=Message,
               responses={400: {"model": Message}, 404: {"model": Message}},
               summary="Delete a reading")
def delete_reading(reading_id: str):
    result = get_collection().delete_one({"_id": _object_id(reading_id)})
    if result.deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Reading {reading_id} not found.")
    return {"detail": f"Reading {reading_id} deleted."}
