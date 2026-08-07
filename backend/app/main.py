from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.db.database import init_db
from app.scheduler import setup_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    setup_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="SectorPulse", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
