from pathlib import Path

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

app = FastAPI(title="SectorPulse", version="0.1.0")


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health() -> dict:
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
