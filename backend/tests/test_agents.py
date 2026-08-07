"""Tests for agent modules — model instantiation and date-safety checks."""

import re
from pathlib import Path

import pytest

from app.agents.macro_analyst import CyclePhase
from app.agents.portfolio_allocator import PortfolioAllocation
from app.agents.sector_analyst import SectorAnalysis, SectorScore


# --- Model instantiation tests ---


def test_cycle_phase_instantiation():
    phase = CyclePhase(
        phase="expansion",
        confidence=0.85,
        reasoning="Strong PMI and low VIX",
        risk_level="low",
    )
    assert phase.phase == "expansion"
    assert phase.confidence == 0.85
    assert phase.risk_level == "low"


def test_sector_score_instantiation():
    score = SectorScore(ticker="XLK", score=78.5, reasoning="Tech leadership")
    assert score.ticker == "XLK"
    assert score.score == 78.5


def test_sector_analysis_instantiation():
    analysis = SectorAnalysis(
        sectors=[
            SectorScore(ticker="XLK", score=78.5, reasoning="Tech leadership"),
            SectorScore(ticker="XLV", score=65.0, reasoning="Defensive strength"),
        ]
    )
    assert len(analysis.sectors) == 2


def test_portfolio_allocation_instantiation():
    alloc = PortfolioAllocation(
        weights={"XLK": 0.4, "XLV": 0.3, "XLI": 0.3},
        reasoning="Balanced growth and defense",
    )
    assert abs(sum(alloc.weights.values()) - 1.0) < 1e-9
    assert len(alloc.weights) == 3


def test_portfolio_allocation_weights_validation():
    alloc = PortfolioAllocation(
        weights={"XLK": 1.0},
        reasoning="Concentrated bet",
    )
    assert alloc.weights["XLK"] == 1.0


# --- Date-safety tests ---

# Pattern that catches date-like references in prompt templates.
# Looks for common date words that should NOT appear in prompts passed to the LLM.
# We allow them in comments/docstrings/variable names but not in prompt string content.
_DATE_PATTERN = re.compile(
    r"""(?x)
    # Match date-related words inside string literals (single or double quoted)
    # that are likely part of prompt templates
    \b(
        january|february|march|april|may|june|july|august|september|
        october|november|december|
        Q[1-4]\s*20\d{2}|          # Q1 2024 etc
        20\d{2}[-/]\d{2}|          # 2024-01 etc
        \d{2}[-/]\d{2}[-/]20\d{2}  # 01/15/2024 etc
    )\b
    """,
    re.IGNORECASE,
)

AGENTS_DIR = Path(__file__).parent.parent / "app" / "agents"


def _get_prompt_strings(filepath: Path) -> list[str]:
    """Extract string content from _SYSTEM_PROMPT and user_prompt variables."""
    content = filepath.read_text()
    # Find all string literals that are part of prompt definitions
    # We look for content inside _SYSTEM_PROMPT and user_prompt assignments
    prompts = []
    # Extract triple-quoted and parenthesized string concatenations
    # Simple approach: find all string content in _PROMPT variables and user_prompt
    in_prompt = False
    for line in content.split("\n"):
        stripped = line.strip()
        if "_PROMPT" in line or "user_prompt" in line:
            in_prompt = True
        if in_prompt:
            prompts.append(stripped)
        if in_prompt and stripped.endswith(")"):
            in_prompt = False
    return prompts


@pytest.mark.parametrize(
    "agent_file",
    list(AGENTS_DIR.glob("*.py")),
    ids=lambda p: p.name,
)
def test_no_hardcoded_dates_in_prompts(agent_file: Path):
    """Verify no agent prompt contains hardcoded date references.

    This enforces the critical anti-look-ahead-bias rule: agents must never
    receive date information that could trigger historical knowledge.
    """
    if agent_file.name == "__init__.py":
        pytest.skip("No prompts in __init__.py")

    prompt_lines = _get_prompt_strings(agent_file)
    prompt_text = "\n".join(prompt_lines)

    # Allow references in historical examples (they're general patterns, not current dates)
    # Filter out lines that are clearly historical pattern descriptions
    filtered_lines = [
        line
        for line in prompt_lines
        if not any(
            marker in line
            for marker in ["e.g.,", "Historical", "###", "performers:"]
        )
    ]
    filtered_text = "\n".join(filtered_lines)

    matches = _DATE_PATTERN.findall(filtered_text)
    assert not matches, (
        f"{agent_file.name} contains date references in prompts: {matches}. "
        f"Agents must not receive date information (anti-look-ahead-bias rule)."
    )


def test_no_decision_date_parameter():
    """Verify decision_date parameter has been removed from all agent functions."""
    for agent_file in AGENTS_DIR.glob("*.py"):
        if agent_file.name == "__init__.py":
            continue
        content = agent_file.read_text()
        assert "decision_date" not in content, (
            f"{agent_file.name} still contains 'decision_date' parameter. "
            f"This parameter should be removed — agents never pass dates to the LLM."
        )


def test_model_is_sonnet():
    """Verify all agents use claude-sonnet-4-6, not opus."""
    # orchestrator.py delegates to other agents — it doesn't instantiate an LLM
    skip_files = {"__init__.py", "orchestrator.py"}
    for agent_file in AGENTS_DIR.glob("*.py"):
        if agent_file.name in skip_files:
            continue
        content = agent_file.read_text()
        assert "claude-opus-4-6" not in content, (
            f"{agent_file.name} still uses claude-opus-4-6. "
            f"All agents must use claude-sonnet-4-6."
        )
        assert "claude-sonnet-4-6" in content, (
            f"{agent_file.name} does not reference claude-sonnet-4-6."
        )
