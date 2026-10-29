"""Beijing Air Quality API — Task 3: CRUD and time-series endpoints for MySQL and MongoDB.

Run:  uvicorn api.main:app --reload
Docs: http://127.0.0.1:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routers import mongo_readings, sql_readings
from api.sql_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create the SQL tables if this is a fresh database
    yield


app = FastAPI(
    title="Beijing Air Quality API",
    description=(
        "CRUD and time-series query endpoints over the Beijing Multi-Site Air Quality "
        "dataset, stored in both a relational database (`/sql`) and MongoDB (`/mongo`). "
        "Both backends accept and return the same flat reading shape.\n\n"
        "**Note:** the live instance runs on Render's free tier, which sleeps after ~15 minutes "
        "of inactivity. The first request after a pause can take up to a minute; retry if it times out."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(sql_readings.router)
app.include_router(mongo_readings.router)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "docs": "/docs", "backends": ["/sql", "/mongo"]}
