"""REST API routes for SectorPulse."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import run_analysis
from app.db.crud import create_report, get_latest_report, get_report_by_id, get_reports
from app.db.database import get_db
from app.scheduler import get_scheduler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# --- Rate limiting (in-memory, resets at midnight ET) ---

_rate_limit_state: dict[str, object] = {"date": None, "count": 0}
_MAX_RUNS_PER_DAY = 3


def _check_rate_limit() -> None:
    """Raise 429 if daily run limit exceeded. Resets at midnight ET."""
    et_now = datetime.now(ZoneInfo("America/New_York"))
    today = et_now.date()

    if _rate_limit_state["date"] != today:
        _rate_limit_state["date"] = today
        _rate_limit_state["count"] = 0

    if _rate_limit_state["count"] >= _MAX_RUNS_PER_DAY:  # type: ignore[operator]
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {_MAX_RUNS_PER_DAY} runs per day",
        )

    _rate_limit_state["count"] += 1  # type: ignore[operator]


def _report_to_dict(report) -> dict:
    """Convert a Report ORM object to a JSON-serializable dict."""
    return {
        "id": report.id,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "trigger": report.trigger,
        "cycle_phase": report.cycle_phase,
        "cycle_confidence": report.cycle_confidence,
        "risk_level": report.risk_level,
        "narrative": report.narrative,
        "sector_scores": report.sector_scores,
        "allocation": report.allocation,
        "rrg_data": report.rrg_data,
        "raw_macro_data": report.raw_macro_data,
    }


def _report_summary(report) -> dict:
    """Convert a Report to a summary dict (list view)."""
    return {
        "id": report.id,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "cycle_phase": report.cycle_phase,
        "risk_level": report.risk_level,
        "trigger": report.trigger,
    }


# --- Endpoints ---


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    latest = await get_latest_report(db)
    last_run = latest.created_at.isoformat() if latest else None
    return {"status": "ok", "last_run": last_run}


@router.get("/reports")
async def list_reports(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    reports = await get_reports(db, limit=limit, offset=offset)
    return [_report_summary(r) for r in reports]


@router.get("/reports/latest")
async def latest_report(db: AsyncSession = Depends(get_db)) -> dict:
    report = await get_latest_report(db)
    if report is None:
        raise HTTPException(status_code=404, detail="No reports found")
    return _report_to_dict(report)


@router.get("/reports/{report_id}")
async def get_report(report_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    report = await get_report_by_id(db, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return _report_to_dict(report)


@router.post("/run", status_code=201)
async def trigger_run(db: AsyncSession = Depends(get_db)) -> dict:
    _check_rate_limit()

    result = await run_analysis(trigger="manual")

    report_data = {
        "trigger": result.trigger,
        "cycle_phase": result.cycle_phase.phase if result.cycle_phase else "unknown",
        "cycle_confidence": result.cycle_phase.confidence if result.cycle_phase else 0.0,
        "risk_level": result.cycle_phase.risk_level if result.cycle_phase else "unknown",
        "narrative": result.narrative.market_narrative if result.narrative else "",
        "sector_scores": (
            {s.ticker: s.score for s in result.sector_analysis.sectors}
            if result.sector_analysis
            else {}
        ),
        "allocation": result.allocation.weights if result.allocation else {},
        "rrg_data": result.rrg_data,
        "raw_macro_data": result.macro_snapshot,
    }

    report = await create_report(db, report_data)
    return _report_to_dict(report)


@router.get("/sectors")
async def sectors(db: AsyncSession = Depends(get_db)) -> dict:
    report = await get_latest_report(db)
    if report is None:
        raise HTTPException(status_code=404, detail="No reports found")
    return {
        "sector_scores": report.sector_scores,
        "allocation": report.allocation,
    }


@router.get("/schedule")
async def schedule() -> dict:
    """Return scheduler status and next scheduled run time."""
    scheduler = get_scheduler()
    if scheduler is None:
        return {"active": False, "next_run": None}

    job = scheduler.get_job("daily_analysis")
    next_run = None
    if job and job.next_run_time:
        next_run = job.next_run_time.isoformat()

    return {"active": True, "next_run": next_run}


@router.get("/sectors/rrg")
async def sectors_rrg(db: AsyncSession = Depends(get_db)) -> dict:
    report = await get_latest_report(db)
    if report is None:
        raise HTTPException(status_code=404, detail="No reports found")
    return {"rrg_data": report.rrg_data}
