"""V2 Sector Analyst — multi-timeframe momentum + historical cycle-sector few-shot."""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

from app.agents.macro_analyst import CyclePhase


class SectorScore(BaseModel):
    """Score for an individual sector ETF."""

    ticker: str = Field(description="Sector ETF ticker symbol")
    score: float = Field(description="Attractiveness score from 0.0 to 100.0")
    reasoning: str = Field(description="Explanation for the score")


class SectorAnalysis(BaseModel):
    """Aggregated sector scoring output."""

    sectors: list[SectorScore] = Field(description="Scored list of sector ETFs")


# Historical cycle-sector performance patterns (empirical data)
_HISTORICAL_EXAMPLES = """
## Historical Sector Performance by Cycle Phase (empirical averages)

### Recovery (e.g., 2009 Q2-Q4, 2020 Q3-Q4):
- TOP performers: XLF (+45%), XLY (+38%), XLI (+32%), XLB (+30%), XLRE (+28%)
- BOTTOM performers: XLU (+8%), XLP (+12%), XLV (+15%)
- Pattern: beaten-down cyclicals snap back hardest; defensives lag

### Expansion (e.g., 2013-2014, 2017-2018):
- TOP performers: XLK (+22%), XLY (+18%), XLI (+16%), XLC (+15%)
- BOTTOM performers: XLU (+5%), XLP (+6%), XLE (+8%)
- Pattern: growth/tech leadership; energy depends on oil cycle

### Slowdown (e.g., 2007 H2, 2019 H2, 2022 H1):
- TOP performers: XLE (+15%), XLV (+8%), XLP (+6%), XLU (+5%)
- BOTTOM performers: XLF (-5%), XLY (-8%), XLRE (-10%)
- Pattern: commodity/defensive rotation; rate-sensitive sectors suffer

### Contraction (e.g., 2008 Q4, 2020 Q1):
- TOP performers: XLV (-8%), XLP (-10%), XLU (-12%)
- BOTTOM performers: XLF (-35%), XLY (-30%), XLE (-28%), XLI (-25%)
- Pattern: everything falls, but defensives lose least; quality matters
"""

_SYSTEM_PROMPT = (
    "You are a sector rotation analyst. Given the current business cycle phase, "
    "multi-timeframe sector momentum data, and risk level, score each available "
    "sector ETF on attractiveness from 0 to 100.\n\n"
    "IMPORTANT: Follow this structured scoring framework:\n"
    "1. CYCLE ALIGNMENT (40%): How well does this sector historically perform in "
    "the current cycle phase? Use the historical examples provided.\n"
    "2. MOMENTUM CONFIRMATION (35%): Do the multi-timeframe signals confirm? "
    "Look for: (a) all timeframes positive = strong trend, (b) short-term turning "
    "up while long-term negative = potential reversal, (c) short-term negative "
    "while long-term positive = pullback opportunity or trend weakening.\n"
    "3. RISK ADJUSTMENT (25%): In elevated/high risk environments, favor defensives "
    "(XLV, XLP, XLU) and penalize high-beta cyclicals (XLF, XLY, XLI).\n\n"
    + _HISTORICAL_EXAMPLES
    + "\nCRITICAL RULES:\n"
    "- Score each sector independently. Use ONLY the data provided.\n"
    "- You are NOT given a date. Do NOT try to infer what time period this is.\n"
    "- Do NOT reference any specific historical events, crises, or time periods.\n"
    "- The historical examples above are GENERAL patterns, not predictions for any "
    "specific period. Use them as base rates, not as exact playbooks."
)


def analyze(
    available_sectors: list[str],
    sector_returns_multi: dict[str, dict[str, float]],
    cycle_phase: CyclePhase,
) -> SectorAnalysis:
    """Score sectors using multi-timeframe momentum and cycle alignment.

    Parameters
    ----------
    available_sectors : list[str]
        Ticker symbols of tradeable sector ETFs.
    sector_returns_multi : dict[str, dict[str, float]]
        Multi-timeframe returns per sector. Keys are tickers, values are dicts
        with keys like "1m", "3m", "6m", "12m".
    cycle_phase : CyclePhase
        Current business cycle classification from the macro analyst.
    """
    llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)
    structured_llm = llm.with_structured_output(SectorAnalysis)

    returns_lines = []
    for ticker in sorted(available_sectors):
        if ticker in sector_returns_multi:
            rets = sector_returns_multi[ticker]
            parts = [f"{tf}: {r:+.4f}" for tf, r in sorted(rets.items())]
            returns_lines.append(f"- {ticker}: {', '.join(parts)}")
        else:
            returns_lines.append(f"- {ticker}: no data")
    returns_text = "\n".join(returns_lines)

    user_prompt = (
        "The business cycle is in the "
        f"**{cycle_phase.phase}** phase (confidence: {cycle_phase.confidence:.2f}, "
        f"risk level: {cycle_phase.risk_level}).\n"
        f"Reasoning: {cycle_phase.reasoning}\n\n"
        f"Available sector ETFs: {', '.join(sorted(available_sectors))}\n\n"
        f"Multi-timeframe sector returns (1m/3m/6m/12m):\n{returns_text}\n\n"
        "Score each available sector from 0 to 100 using the structured framework:\n"
        "1. Cycle alignment (40%)\n"
        "2. Momentum confirmation (35%)\n"
        "3. Risk adjustment (25%)\n\n"
        "Provide reasoning for each score."
    )

    result = structured_llm.invoke(
        [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )
    return result
