"""APScheduler integration — daily analysis at 4:30 PM ET."""

from __future__ import annotations

import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None

JOB_ID = "daily_analysis"


async def _run_scheduled_analysis() -> None:
    """Job callback: run the analysis pipeline and persist the result."""
    from app.agents.orchestrator import run_analysis
    from app.db.crud import create_report
    from app.db.database import async_session_factory

    logger.info("Scheduled analysis starting")
    try:
        result = await run_analysis(trigger="scheduled")

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

        async with async_session_factory() as session:
            await create_report(session, report_data)
        logger.info("Scheduled analysis completed and saved")
    except Exception:
        logger.exception("Scheduled analysis failed")


def setup_scheduler() -> AsyncIOScheduler | None:
    """Create and start the scheduler. Returns None if ANTHROPIC_API_KEY is not set."""
    global _scheduler

    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.warning("ANTHROPIC_API_KEY not set — scheduler disabled")
        return None

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _run_scheduled_analysis,
        trigger=CronTrigger(hour=16, minute=30, timezone="US/Eastern"),
        id=JOB_ID,
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started — daily analysis at 4:30 PM ET")
    return _scheduler


def shutdown_scheduler() -> None:
    """Shut down the scheduler if running."""
    global _scheduler
    if _scheduler is not None:
        try:
            if _scheduler.running:
                _scheduler.shutdown(wait=False)
                logger.info("Scheduler shut down")
        except RuntimeError:
            pass  # event loop already closed
        _scheduler = None


def get_scheduler() -> AsyncIOScheduler | None:
    """Return the current scheduler instance (or None)."""
    return _scheduler
