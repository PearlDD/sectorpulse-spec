"""Narrative generator — produces human-readable market stories from analysis results."""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

from app.agents.macro_analyst import CyclePhase
from app.agents.portfolio_allocator import PortfolioAllocation
from app.agents.sector_analyst import SectorAnalysis


class NarrativeReport(BaseModel):
    """Human-readable narrative output."""

    market_narrative: str = Field(
        description="2-3 paragraph macro story describing the market environment"
    )
    sector_explanations: dict[str, str] = Field(
        description="Ticker → explanation of why this sector is hot or cold"
    )


_SYSTEM_PROMPT = (
    "You are a financial market narrator. Given analysis results including a "
    "business cycle phase, sector scores, and portfolio allocation weights, "
    "write a clear, compelling market narrative.\n\n"
    "Your output has two parts:\n"
    "1. market_narrative: A 2-3 paragraph macro story explaining the current "
    "market environment. Describe the economic landscape using the indicators "
    "and scores provided. Explain why certain sectors are favored.\n"
    "2. sector_explanations: For each sector that was scored, provide a concise "
    "explanation of WHY it is attractive or unattractive right now.\n\n"
    "CRITICAL RULES:\n"
    "- Do not reference any specific dates, months, quarters, or years. "
    "Describe the market environment using only economic indicators and their "
    "current values.\n"
    "- Do NOT try to infer what time period this is.\n"
    "- Do NOT reference any specific historical events, crises, or time periods.\n"
    "- Base your narrative PURELY on the data provided."
)


def generate(
    cycle_phase: CyclePhase,
    sector_analysis: SectorAnalysis,
    allocation: PortfolioAllocation,
) -> NarrativeReport:
    """Generate a narrative report from analysis results."""
    llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)
    structured_llm = llm.with_structured_output(NarrativeReport)

    scores_text = "\n".join(
        f"- {s.ticker}: score {s.score:.1f} — {s.reasoning}"
        for s in sorted(sector_analysis.sectors, key=lambda x: x.score, reverse=True)
    )

    weights_text = "\n".join(
        f"- {t}: {w:.1%}"
        for t, w in sorted(allocation.weights.items(), key=lambda x: x[1], reverse=True)
    )

    user_prompt = (
        f"**Cycle Phase**: {cycle_phase.phase} "
        f"(confidence: {cycle_phase.confidence:.2f})\n"
        f"**Risk Level**: {cycle_phase.risk_level}\n"
        f"**Cycle Reasoning**: {cycle_phase.reasoning}\n\n"
        f"**Sector Scores** (sorted by attractiveness):\n{scores_text}\n\n"
        f"**Portfolio Allocation**:\n{weights_text}\n"
        f"**Allocation Reasoning**: {allocation.reasoning}\n\n"
        "Write a market narrative and sector explanations based on the above data. "
        "Do not reference any specific dates, months, quarters, or years. "
        "Describe the market environment using only economic indicators and "
        "their current values."
    )

    result = structured_llm.invoke(
        [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )
    return result
