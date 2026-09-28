"""V2 Portfolio Allocator — risk-aware allocation with reflection step."""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

from app.agents.macro_analyst import CyclePhase
from app.agents.sector_analyst import SectorAnalysis


class PortfolioAllocation(BaseModel):
    """Final portfolio allocation output."""

    weights: dict[str, float] = Field(
        description="Portfolio weights by sector ticker, summing to 1.0"
    )
    reasoning: str = Field(description="Explanation of the allocation decision")


_SYSTEM_PROMPT = (
    "You are a portfolio allocator for a sector rotation strategy. Given the macro "
    "cycle analysis (including risk level) and sector scores, determine the optimal "
    "portfolio allocation.\n\n"
    "Constraints:\n"
    "- Select at most 5 sectors\n"
    "- All weights must be non-negative\n"
    "- Weights must sum to 1.0\n"
    "- Concentrate in the highest-conviction sectors\n\n"
    "RISK-AWARE RULES:\n"
    "- If risk_level is 'elevated': cap max single position at 30%, ensure >=1 defensive sector\n"
    "- If risk_level is 'high': cap max single position at 25%, ensure >=2 defensive sectors "
    "(XLV, XLP, XLU), reduce total positions to 3-4\n"
    "- Defensive sectors: XLV (Healthcare), XLP (Consumer Staples), XLU (Utilities)\n\n"
    "REFLECTION: Before finalizing, check:\n"
    "1. Does the allocation match the cycle phase? (e.g., not heavy cyclicals in contraction)\n"
    "2. Is concentration appropriate for the confidence level?\n"
    "3. Would this allocation survive a -10% market shock?\n\n"
    "CRITICAL RULES:\n"
    "- Use ONLY the data provided.\n"
    "- You are NOT given a date. Do NOT try to infer what time period this is.\n"
    "- Do NOT reference any specific historical events, crises, or time periods.\n"
    "- Base decisions PURELY on the scores, cycle phase, and risk level provided."
)


def allocate(
    cycle_phase: CyclePhase,
    sector_scores: SectorAnalysis,
    available_sectors: list[str],
) -> PortfolioAllocation:
    """Produce risk-aware portfolio weights with reflection."""
    llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)
    structured_llm = llm.with_structured_output(PortfolioAllocation)

    scores_text = "\n".join(
        f"- {s.ticker}: {s.score:.1f} — {s.reasoning}"
        for s in sorted(sector_scores.sectors, key=lambda x: x.score, reverse=True)
    )

    user_prompt = (
        "Allocate a sector rotation portfolio.\n\n"
        f"**Cycle Phase**: {cycle_phase.phase} (confidence: {cycle_phase.confidence:.2f})\n"
        f"**Risk Level**: {cycle_phase.risk_level}\n"
        f"Cycle reasoning: {cycle_phase.reasoning}\n\n"
        f"**Sector Scores** (sorted by attractiveness):\n{scores_text}\n\n"
        f"Available sectors: {', '.join(sorted(available_sectors))}\n\n"
        "Allocate weights to at most 5 sectors following the risk-aware rules. "
        "Before finalizing, perform the reflection check. "
        "Explain your allocation rationale including reflection results."
    )

    result = structured_llm.invoke(
        [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )

    result = _enforce_constraints(result, available_sectors)
    return result


def _enforce_constraints(
    allocation: PortfolioAllocation,
    available_sectors: list[str],
) -> PortfolioAllocation:
    """Enforce portfolio constraints: max 5 sectors, no negatives, sum to 1.0."""
    clean = {
        t: max(w, 0.0)
        for t, w in allocation.weights.items()
        if t in available_sectors and w > 0
    }

    if len(clean) > 5:
        top5 = sorted(clean.items(), key=lambda x: x[1], reverse=True)[:5]
        clean = dict(top5)

    total = sum(clean.values())
    if total > 0:
        clean = {t: w / total for t, w in clean.items()}
    else:
        fallback = available_sectors[:5]
        clean = {t: 1.0 / len(fallback) for t in fallback}

    return PortfolioAllocation(weights=clean, reasoning=allocation.reasoning)
