import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.staticfiles import StaticFiles

from app.logging_config import request_id_var, setup_logging

setup_logging()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request ID middleware
# ---------------------------------------------------------------------------

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Generates (or reads) a unique request ID and stores it in a ContextVar."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            request_id_var.reset(token)


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SectorPulse starting up")
    yield
    logger.info("SectorPulse shutting down")


app = FastAPI(title="SectorPulse", version="0.1.0", lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health() -> dict:
    logger.info("Health check")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# SPA static file serving — catches 404s and returns index.html
# ---------------------------------------------------------------------------

class SPAStaticFiles(StaticFiles):
    """StaticFiles subclass that falls back to index.html for SPA routing."""

    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
            if response.status_code == 404:
                return await self._index_response(scope)
            return response
        except Exception:
            return await self._index_response(scope)

    async def _index_response(self, scope):
        return await super().get_response("index.html", scope)


# Mount SPA AFTER API routes so /api/* always takes precedence.
# check_dir=False so dev mode (Vite proxy) doesn't crash on missing dist/.
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
app.mount(
    "/",
    SPAStaticFiles(directory=str(_frontend_dist), html=True, check_dir=False),
    name="spa",
)
