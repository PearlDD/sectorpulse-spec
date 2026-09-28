import logging
import os
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from app.analysis import METHOD_VERSION
from app.data.fetcher import resolve_date
from app.db.store import Store
from app.services.explanation import configured
from app.services.jobs import JobRunner, calculate

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
Mode = Literal["live", "demo"]


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    as_of_date: date | None = None
    mode: Mode = "live"


@asynccontextmanager
async def lifespan(app: FastAPI):
    path = os.getenv(
        "SECTORPULSE_DB",
        str(Path(__file__).resolve().parents[2] / "data" / "sectorpulse.db"),
    )
    store = Store(str(Path(path).resolve()))
    runner = JobRunner(store)
    runner.start()
    app.state.store, app.state.runner = store, runner
    try:
        yield
    finally:
        runner.close()


app = FastAPI(title="SectorPulse", version="0.3.0", lifespan=lifespan)


def storage(request: Request) -> Store:
    return request.app.state.store


def require_run(store: Store, run_id: str) -> dict:
    try:
        return store.run(run_id)
    except KeyError:
        raise HTTPException(
            404, detail={"code": "run_not_found", "message": "Saved run not found"}
        ) from None


def enqueue(store: Store, kind: str, params: dict) -> dict:
    try:
        job, reused = store.enqueue(kind, params)
    except ValueError:
        raise HTTPException(
            429,
            detail={
                "code": "queue_full",
                "message": "Worker queue is full. Read saved results and retry later.",
            },
        ) from None
    return {"job": job, "deduplicated": reused}


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": "0.3.0",
        "fred_configured": bool(os.getenv("FRED_API_KEY", "").strip()),
        "ai_enabled": configured(),
        "method_version": METHOD_VERSION,
    }


@app.post("/api/runs", status_code=202)
def start_run(body: RunRequest, request: Request) -> dict:
    try:
        end = resolve_date(body.as_of_date)
    except ValueError as exc:
        raise HTTPException(
            422, detail={"code": "invalid_date", "message": str(exc)}
        ) from None
    return enqueue(
        storage(request),
        "analysis",
        {
            "as_of_date": end.isoformat(),
            "mode": body.mode,
            "method_version": METHOD_VERSION,
        },
    )


@app.get("/api/jobs")
def jobs(request: Request) -> list[dict]:
    return storage(request).jobs()


@app.get("/api/jobs/{job_id}")
def job(job_id: str, request: Request) -> dict:
    try:
        return storage(request).job(job_id)
    except KeyError:
        raise HTTPException(
            404, detail={"code": "job_not_found", "message": "Task not found"}
        ) from None


@app.get("/api/runs")
def runs(
    request: Request,
    mode: Mode | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    return storage(request).runs(mode, limit, offset)


@app.get("/api/runs/latest")
def latest(request: Request, mode: Mode = "live") -> dict:
    rows = storage(request).runs(mode, 1)
    if not rows:
        raise HTTPException(
            404,
            detail={
                "code": "no_saved_runs",
                "message": "No saved analysis for this data source. Refresh to create one.",
            },
        )
    return storage(request).run(rows[0]["id"])


@app.get("/api/runs/{run_id}")
def run(run_id: str, request: Request) -> dict:
    return require_run(storage(request), run_id)


@app.get("/api/runs/{run_id}/snapshot")
def snapshot(run_id: str, request: Request) -> dict:
    record = require_run(storage(request), run_id)
    return storage(request).read_snapshot(record["snapshot_id"])


@app.get("/api/runs/{run_id}/replay")
def replay(run_id: str, request: Request) -> dict:
    record = require_run(storage(request), run_id)
    if record["method_version"] != METHOD_VERSION:
        raise HTTPException(
            409,
            detail={
                "code": "method_version_mismatch",
                "message": "Replay requires the original calculation version.",
            },
        )
    saved = storage(request).read_snapshot(record["snapshot_id"])
    result = calculate(saved["payload"])
    matches = all(record.get(key) == value for key, value in result.items())
    return {
        "snapshot_sha256": saved["sha256"],
        "matches_saved": matches,
        "result": result,
    }


@app.get("/api/runs/{run_id}/explanation")
def read_explanation(run_id: str, request: Request) -> dict:
    require_run(storage(request), run_id)
    result = storage(request).explanation(run_id)
    return {
        "status": "available" if result else "not_requested",
        "enabled": configured(),
        "explanation": result,
    }


@app.post("/api/runs/{run_id}/explanation", status_code=202)
def start_explanation(run_id: str, request: Request) -> dict:
    require_run(storage(request), run_id)
    if not configured():
        raise HTTPException(
            503,
            detail={
                "code": "ai_not_configured",
                "message": "Optional AI requires a server-side ANTHROPIC_API_KEY. Calculations are unaffected.",
            },
        )
    if storage(request).explanation(run_id):
        return {"cached": True, "explanation": storage(request).explanation(run_id)}
    return enqueue(storage(request), "explanation", {"run_id": run_id})


# Compatibility reads: cached only, never start provider calls on GET.
@app.get("/api/analysis")
def analysis(
    request: Request, mode: Mode = "live", as_of_date: date | None = None
) -> dict:
    record = latest(request, mode)
    if as_of_date and record["as_of_date"] != as_of_date.isoformat():
        raise HTTPException(
            404,
            detail={
                "code": "no_matching_run",
                "message": "Use POST /api/runs to request this date.",
            },
        )
    return record


@app.get("/api/prices")
def prices(
    request: Request, mode: Mode = "live", as_of_date: date | None = None
) -> dict:
    record = analysis(request, mode, as_of_date)
    return {
        "run_id": record["id"],
        "as_of_date": record["as_of_date"],
        "source": record["source"],
        "series": record["prices"],
        "unavailable": record["excluded"],
    }


@app.get("/api/macro")
def macro(
    request: Request, mode: Mode = "live", as_of_date: date | None = None
) -> dict:
    record = analysis(request, mode, as_of_date)
    return {
        "run_id": record["id"],
        "as_of_date": record["as_of_date"],
        **record["macro"],
    }


static_dir = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="dashboard")
