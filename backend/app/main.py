import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Tuple

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from app.api.routes import router  # noqa: E402
from app.db.database import init_db  # noqa: E402
from app.scheduler import setup_scheduler, shutdown_scheduler  # noqa: E402

_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


class SPAStaticFiles(StaticFiles):
    def lookup_path(
        self, path: str
    ) -> Tuple[str, Optional[os.stat_result]]:
        full_path, stat_result = super().lookup_path(path)
        if stat_result is None:
            return super().lookup_path("./index.html")
        return full_path, stat_result


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

# SPA static file serving — must be after API routes
if _frontend_dist.is_dir():
    app.mount("/", SPAStaticFiles(directory=str(_frontend_dist), html=True), name="spa")
