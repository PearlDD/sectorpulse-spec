from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.database import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="SectorPulse", version="0.1.0", lifespan=lifespan)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
