"""Tests for orchestrator and narrative generator."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from app.agents.macro_analyst import CyclePhase
from app.agents.narrative_gen import NarrativeReport, _SYSTEM_PROMPT
from app.agents.orchestrator import (
    AnalysisResult,
    _compute_multi_timeframe_returns,
    run_analysis,
)
from app.agents.portfolio_allocator import PortfolioAllocation
from app.agents.sector_analyst import SectorAnalysis, SectorScore


# ---------------------------------------------------------------------------
# AnalysisResult model tests
# ---------------------------------------------------------------------------


def test_analysis_result_defaults():
    result = AnalysisResult(trigger="manual")
    assert result.trigger == "manual"
    assert result.cycle_phase is None
    assert result.sector_analysis is None
    assert result.allocation is None
    assert result.narrative is None
    assert result.rrg_data == {}
    assert result.oversold == []
    assert result.macro_snapshot == {}
    assert result.errors == []
    assert result.latency_ms == 0.0


def test_analysis_result_with_data():
    phase = CyclePhase(
        phase="expansion",
        confidence=0.85,
        reasoning="Strong growth",
        risk_level="low",
    )
    result = AnalysisResult(
        trigger="scheduled",
        cycle_phase=phase,
        macro_snapshot={"ISM_PMI": 55.0, "VIX": 14.0},
    )
    assert result.trigger == "scheduled"
    assert result.cycle_phase.phase == "expansion"
    assert result.macro_snapshot["VIX"] == 14.0


def test_analysis_result_trigger_values():
    for trigger in ("manual", "scheduled"):
        result = AnalysisResult(trigger=trigger)
        assert result.trigger == trigger


# ---------------------------------------------------------------------------
# NarrativeReport model tests
# ---------------------------------------------------------------------------


def test_narrative_report_instantiation():
    report = NarrativeReport(
        market_narrative="The economy is expanding.",
        sector_explanations={"XLK": "Tech is leading", "XLV": "Healthcare is defensive"},
    )
    assert "expanding" in report.market_narrative
    assert len(report.sector_explanations) == 2


# ---------------------------------------------------------------------------
# Narrative prompt date-safety tests
# ---------------------------------------------------------------------------

NARRATIVE_FILE = Path(__file__).parent.parent / "app" / "agents" / "narrative_gen.py"


def test_narrative_system_prompt_has_no_date_instruction():
    """The system prompt must explicitly instruct the LLM not to use dates."""
    assert "Do not reference any specific dates" in _SYSTEM_PROMPT
    assert "months" in _SYSTEM_PROMPT
    assert "quarters" in _SYSTEM_PROMPT
    assert "years" in _SYSTEM_PROMPT


def test_narrative_prompt_no_hardcoded_dates():
    """Verify narrative_gen.py contains no hardcoded date references in prompts."""
    import re

    content = NARRATIVE_FILE.read_text()

    date_pattern = re.compile(
        r"""(?x)
        \b(
            january|february|march|april|may|june|july|august|september|
            october|november|december|
            Q[1-4]\s*20\d{2}|
            20\d{2}[-/]\d{2}|
            \d{2}[-/]\d{2}[-/]20\d{2}
        )\b
        """,
        re.IGNORECASE,
    )

    # Extract prompt-related lines (same approach as test_agents.py)
    prompt_lines = []
    in_prompt = False
    for line in content.split("\n"):
        stripped = line.strip()
        if "_PROMPT" in line or "user_prompt" in line:
            in_prompt = True
        if in_prompt:
            prompt_lines.append(stripped)
        if in_prompt and stripped.endswith(")"):
            in_prompt = False

    filtered_lines = [
        line
        for line in prompt_lines
        if not any(
            marker in line
            for marker in ["e.g.,", "Historical", "###", "performers:"]
        )
    ]
    filtered_text = "\n".join(filtered_lines)
    matches = date_pattern.findall(filtered_text)
    assert not matches, (
        f"narrative_gen.py contains date references in prompts: {matches}"
    )


def test_narrative_uses_sonnet():
    """Verify narrative generator uses claude-sonnet-4-6."""
    content = NARRATIVE_FILE.read_text()
    assert "claude-opus-4-6" not in content
    assert "claude-sonnet-4-6" in content


# ---------------------------------------------------------------------------
# Multi-timeframe returns helper
# ---------------------------------------------------------------------------


def test_compute_multi_timeframe_returns():
    dates = pd.date_range("2025-01-01", periods=30, freq="B")
    prices = pd.DataFrame(
        {
            "XLK": np.linspace(100, 110, 30),
            "XLV": np.linspace(50, 48, 30),
        },
        index=dates,
    )
    result = _compute_multi_timeframe_returns(prices, ["XLK", "XLV"])
    assert "XLK" in result
    assert "XLV" in result
    # With 30 days of data we should get at least 1m returns
    assert "1m" in result["XLK"]
    # XLK went up, XLV went down
    assert result["XLK"]["1m"] > 0
    assert result["XLV"]["1m"] < 0


def test_compute_multi_timeframe_returns_missing_ticker():
    dates = pd.date_range("2025-01-01", periods=30, freq="B")
    prices = pd.DataFrame({"XLK": np.linspace(100, 110, 30)}, index=dates)
    result = _compute_multi_timeframe_returns(prices, ["XLK", "MISSING"])
    assert "XLK" in result
    assert "MISSING" not in result


# ---------------------------------------------------------------------------
# Orchestrator flow test (mocked agents)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_analysis_flow():
    """Test the orchestrator flow with mocked external calls."""
    dates = pd.date_range("2025-01-01", periods=30, freq="B")
    mock_prices = pd.DataFrame(
        {
            "XLK": np.linspace(100, 110, 30),
            "XLV": np.linspace(50, 52, 30),
            "SPY": np.linspace(400, 410, 30),
        },
        index=dates,
    )

    mock_phase = CyclePhase(
        phase="expansion",
        confidence=0.85,
        reasoning="Strong PMI",
        risk_level="low",
    )

    mock_scores = SectorAnalysis(
        sectors=[
            SectorScore(ticker="XLK", score=80.0, reasoning="Tech leads"),
            SectorScore(ticker="XLV", score=60.0, reasoning="Defensive"),
        ]
    )

    mock_alloc = PortfolioAllocation(
        weights={"XLK": 0.6, "XLV": 0.4},
        reasoning="Growth tilt",
    )

    mock_narrative = NarrativeReport(
        market_narrative="The economy is expanding with strong growth signals.",
        sector_explanations={"XLK": "Tech leadership", "XLV": "Defensive play"},
    )

    with (
        patch("app.agents.orchestrator.fetch_sector_prices", return_value=mock_prices),
        patch(
            "app.agents.orchestrator.get_latest_macro_snapshot",
            return_value={"ISM_PMI": 55.0, "VIX": 14.0},
        ),
        patch("app.agents.orchestrator.macro_analyze", return_value=mock_phase),
        patch("app.agents.orchestrator.sector_analyze", return_value=mock_scores),
        patch("app.agents.orchestrator.portfolio_allocate", return_value=mock_alloc),
        patch("app.agents.orchestrator.narrative_generate", return_value=mock_narrative),
    ):
        result = await run_analysis(trigger="manual")

    assert result.trigger == "manual"
    assert result.cycle_phase == mock_phase
    assert result.sector_analysis == mock_scores
    assert result.allocation == mock_alloc
    assert result.narrative == mock_narrative
    assert result.macro_snapshot == {"ISM_PMI": 55.0, "VIX": 14.0}
    assert result.latency_ms > 0
    assert result.errors == []


@pytest.mark.asyncio
async def test_run_analysis_agent_failure_captured():
    """Test that agent failures are captured in errors and pipeline continues."""
    dates = pd.date_range("2025-01-01", periods=30, freq="B")
    mock_prices = pd.DataFrame(
        {
            "XLK": np.linspace(100, 110, 30),
            "SPY": np.linspace(400, 410, 30),
        },
        index=dates,
    )

    mock_phase = CyclePhase(
        phase="expansion",
        confidence=0.85,
        reasoning="Strong PMI",
        risk_level="low",
    )

    mock_scores = SectorAnalysis(
        sectors=[SectorScore(ticker="XLK", score=80.0, reasoning="Tech")]
    )

    mock_alloc = PortfolioAllocation(
        weights={"XLK": 1.0},
        reasoning="Concentrated",
    )

    with (
        patch("app.agents.orchestrator.fetch_sector_prices", return_value=mock_prices),
        patch(
            "app.agents.orchestrator.get_latest_macro_snapshot",
            return_value={},
        ),
        patch("app.agents.orchestrator.macro_analyze", return_value=mock_phase),
        patch("app.agents.orchestrator.sector_analyze", return_value=mock_scores),
        patch("app.agents.orchestrator.portfolio_allocate", return_value=mock_alloc),
        patch(
            "app.agents.orchestrator.narrative_generate",
            side_effect=RuntimeError("API error"),
        ),
    ):
        result = await run_analysis(trigger="scheduled")

    # Narrative failed but pipeline continued
    assert result.narrative is None
    assert any("Narrative generator failed" in e for e in result.errors)
    # Other results still populated
    assert result.cycle_phase is not None
    assert result.allocation is not None


@pytest.mark.asyncio
async def test_run_analysis_price_failure_stops_early():
    """If price fetch fails, pipeline returns early with error."""
    with patch(
        "app.agents.orchestrator.fetch_sector_prices",
        side_effect=RuntimeError("Network error"),
    ):
        result = await run_analysis()

    assert result.cycle_phase is None
    assert any("Price fetch failed" in e for e in result.errors)
