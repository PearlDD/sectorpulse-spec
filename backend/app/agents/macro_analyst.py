"""V2 Macro Analyst — adds credit spreads, VIX, and structured analysis framework."""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field


class CyclePhase(BaseModel):
    """Business cycle classification output."""

    phase: str = Field(description="One of: recovery, expansion, slowdown, contraction")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(description="Explanation of the cycle phase determination")
    risk_level: str = Field(
        description="One of: low, moderate, elevated, high — based on credit/VIX signals"
    )


_SYSTEM_PROMPT = (
    "You are a macro-economic analyst specializing in business cycle classification. "
    "Given economic indicators as of a specific date, determine the current phase of "
    "the business cycle. The four phases are:\n"
    "- recovery: economy rebounding from a trough, rising PMI, improving employment, "
    "narrowing credit spreads, falling VIX\n"
    "- expansion: broad economic growth, rising corporate earnings, tightening labor market, "
    "low credit spreads, low VIX\n"
    "- slowdown: growth decelerating, yield curve flattening/inverting, rising claims, "
    "widening credit spreads, rising VIX\n"
    "- contraction: economic decline, falling PMI below 50, rising unemployment, "
    "wide credit spreads, elevated VIX\n\n"
    "IMPORTANT: Follow this structured analysis framework:\n"
    "1. GROWTH signals: PMI trend (current vs previous), employment, LEI\n"
    "2. YIELD CURVE signal: positive = expansion, flat/inverted = slowdown/contraction\n"
    "3. STRESS signals: credit spreads (HY_SPREAD > 5 = stress, > 8 = crisis), "
    "VIX (> 20 = caution, > 30 = fear, > 40 = panic)\n"
    "4. CROSS-CHECK: do stress signals confirm or contradict growth signals?\n\n"
    "Also assess risk_level based on credit/VIX:\n"
    "- low: HY_SPREAD < 4 and VIX < 15\n"
    "- moderate: HY_SPREAD 4-5 or VIX 15-20\n"
    "- elevated: HY_SPREAD 5-7 or VIX 20-30\n"
    "- high: HY_SPREAD > 7 or VIX > 30\n\n"
    "CRITICAL RULES:\n"
    "- Use ONLY the numerical data provided. Do not assume data you are not given.\n"
    "- You are NOT given a date. Do NOT try to infer what time period this is.\n"
    "- Do NOT reference any specific historical events, crises, or time periods.\n"
    "- Base your analysis PURELY on the indicator values, not on pattern-matching "
    "to known historical episodes."
)


def analyze(macro_data: dict) -> CyclePhase:
    """Classify business cycle phase with credit spread and VIX awareness."""
    llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)
    structured_llm = llm.with_structured_output(CyclePhase)

    indicators_text = "\n".join(f"- {k}: {v}" for k, v in sorted(macro_data.items()))

    user_prompt = (
        "The following economic indicators are available:\n\n"
        f"{indicators_text}\n\n"
        "Follow the structured analysis framework:\n"
        "1. Assess GROWTH signals\n"
        "2. Assess YIELD CURVE signal\n"
        "3. Assess STRESS signals (credit spreads + VIX)\n"
        "4. Cross-check for confirmations or divergences\n\n"
        "Classify the current business cycle phase as one of: "
        "recovery, expansion, slowdown, or contraction. "
        "Also classify risk_level as: low, moderate, elevated, or high. "
        "Provide your confidence (0.0 to 1.0) and detailed reasoning."
    )

    result = structured_llm.invoke(
        [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )
    return result
