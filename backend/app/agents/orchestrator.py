"""Orchestrator — sequential analysis pipeline producing a complete report.

Simplified from the source V2 LangGraph orchestrator: no LangGraph, no
triple-run median, no backtest state. Single sequential run through all
analysis stages.
"""

from __future__ import annotations

import logging
import time
from datetime import date

import pandas as pd
from pydantic import BaseModel, Field

from app.agents.macro_analyst import CyclePhase
from app.agents.macro_analyst import analyze as macro_analyze
from app.agents.narrative_gen import NarrativeReport
from app.agents.narrative_gen import generate as narrative_generate
from app.agents.portfolio_allocator import PortfolioAllocation
from app.agents.portfolio_allocator import allocate as portfolio_allocate
from app.agents.sector_analyst import SectorAnalysis
from app.agents.sector_analyst import analyze as sector_analyze
from app.config import BENCHMARK_TICKER, SECTOR_TICKERS, get_available_sectors
from app.data.fetcher import fetch_sector_prices, get_latest_macro_snapshot
from app.data.oversold import detect_oversold
from app.data.rrg import compute_rrg

logger = logging.getLogger(__name__)


class AnalysisResult(BaseModel):
    """Complete output from a single analysis run."""

    trigger: str = Field(description="How the run was triggered: 'scheduled' or 'manual'")
    cycle_phase: CyclePhase | None = Field(default=None)
    sector_analysis: SectorAnalysis | None = Field(default=None)
    allocation: PortfolioAllocation | None = Field(default=None)
    narrative: NarrativeReport | None = Field(default=None)
    rrg_data: dict = Field(default_factory=dict)
    oversold: list[dict] = Field(default_factory=list)
    macro_snapshot: dict[str, float] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    latency_ms: float = Field(default=0.0)


def _compute_multi_timeframe_returns(
    prices_df: pd.DataFrame,
    available_sectors: list[str],
) -> dict[str, dict[str, float]]:
    """Compute 1m, 3m, 6m, 12m cumulative returns per sector from prices."""
    result: dict[str, dict[str, float]] = {}
    windows = {"1m": 21, "3m": 63, "6m": 126, "12m": 252}

    for ticker in available_sectors:
        if ticker not in prices_df.columns:
            continue
        col = prices_df[ticker].dropna()
        if len(col) < 2:
            continue
        # Compute daily returns
        daily_returns = col.pct_change().dropna()
        tf_returns: dict[str, float] = {}
        for label, days in windows.items():
            if len(daily_returns) >= days:
                trailing = daily_returns.iloc[-days:]
                tf_returns[label] = float((1 + trailing).prod() - 1)
            elif len(daily_returns) > 0:
                tf_returns[label] = float((1 + daily_returns).prod() - 1)
        result[ticker] = tf_returns
    return result


async def run_analysis(trigger: str = "manual") -> AnalysisResult:
    """Run the full analysis pipeline.

    Steps:
        1. Fetch sector prices
        2. Fetch macro indicators
        3. Macro analyst → CyclePhase
        4. Sector analyst → SectorAnalysis
        5. Portfolio allocator → PortfolioAllocation
        6. Narrative generator → NarrativeReport
        7. Compute RRG quadrants
        8. Detect oversold sectors
    """
    start_time = time.time()
    result = AnalysisResult(trigger=trigger)
    today = date.today()
    available_sectors = get_available_sectors(today)

    # --- Step 1: Fetch prices ---
    try:
        prices = fetch_sector_prices()
    except Exception as e:
        logger.error("Failed to fetch prices: %s", e)
        result.errors.append(f"Price fetch failed: {e}")
        result.latency_ms = (time.time() - start_time) * 1000
        return result

    # --- Step 2: Fetch macro snapshot ---
    try:
        macro_snapshot = get_latest_macro_snapshot()
        result.macro_snapshot = macro_snapshot
    except Exception as e:
        logger.error("Failed to fetch macro data: %s", e)
        result.errors.append(f"Macro fetch failed: {e}")
        macro_snapshot = {}

    # --- Step 3: Macro analyst ---
    try:
        cycle_phase = macro_analyze(macro_snapshot)
        result.cycle_phase = cycle_phase
    except Exception as e:
        logger.error("Macro analyst failed: %s", e)
        result.errors.append(f"Macro analyst failed: {e}")
        result.latency_ms = (time.time() - start_time) * 1000
        return result

    # --- Step 4: Sector analyst ---
    sector_returns_multi = _compute_multi_timeframe_returns(prices, available_sectors)
    try:
        sector_analysis = sector_analyze(
            available_sectors=available_sectors,
            sector_returns_multi=sector_returns_multi,
            cycle_phase=cycle_phase,
        )
        result.sector_analysis = sector_analysis
    except Exception as e:
        logger.error("Sector analyst failed: %s", e)
        result.errors.append(f"Sector analyst failed: {e}")
        result.latency_ms = (time.time() - start_time) * 1000
        return result

    # --- Step 5: Portfolio allocator ---
    try:
        allocation = portfolio_allocate(
            cycle_phase=cycle_phase,
            sector_scores=sector_analysis,
            available_sectors=available_sectors,
        )
        result.allocation = allocation
    except Exception as e:
        logger.error("Portfolio allocator failed: %s", e)
        result.errors.append(f"Portfolio allocator failed: {e}")
        result.latency_ms = (time.time() - start_time) * 1000
        return result

    # --- Step 6: Narrative generator ---
    try:
        narrative = narrative_generate(
            cycle_phase=cycle_phase,
            sector_analysis=sector_analysis,
            allocation=allocation,
        )
        result.narrative = narrative
    except Exception as e:
        logger.error("Narrative generator failed: %s", e)
        result.errors.append(f"Narrative generator failed: {e}")

    # --- Step 7: RRG ---
    try:
        sector_cols = [c for c in prices.columns if c in SECTOR_TICKERS]
        if BENCHMARK_TICKER in prices.columns and sector_cols:
            rrg_data = compute_rrg(
                prices_df=prices[sector_cols],
                benchmark=prices[BENCHMARK_TICKER],
            )
            result.rrg_data = rrg_data
    except Exception as e:
        logger.error("RRG computation failed: %s", e)
        result.errors.append(f"RRG computation failed: {e}")

    # --- Step 8: Oversold detection ---
    try:
        oversold = detect_oversold(prices, cycle_phase.phase)
        result.oversold = oversold
    except Exception as e:
        logger.error("Oversold detection failed: %s", e)
        result.errors.append(f"Oversold detection failed: {e}")

    result.latency_ms = (time.time() - start_time) * 1000
    logger.info(
        "Analysis complete in %.1fs — phase=%s, %d sectors scored",
        result.latency_ms / 1000,
        cycle_phase.phase,
        len(sector_analysis.sectors) if sector_analysis else 0,
    )
    return result
