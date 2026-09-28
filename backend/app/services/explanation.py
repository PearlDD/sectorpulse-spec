"""Optional narrative over an explicit date-free numeric whitelist."""

import hashlib
import json
import os
import re

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.db.store import encode

PROMPT_VERSION = "numeric-evidence-v2"
MODEL = "claude-sonnet-4-6"
SYSTEM = """Explain descriptive sector research in plain language. Use only the supplied measurements.
Never invent observations, probabilities, dates, forecasts, recommendations, portfolio weights, or causal claims.
Distinguish relative outperformance from absolute gains and mention coverage and data limitations.
Macro observations are context only and never affect ranking. State uncertainty when inputs are absent.
Return only JSON with keys summary (string), observations (array of strings), limitations (array of strings).
No markdown fences. Do not reference any calendar date, year, historical episode, or specific time period."""


class Explanation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_max_length=2400)
    summary: str = Field(min_length=1)
    observations: list[str] = Field(min_length=1, max_length=12)
    limitations: list[str] = Field(min_length=1, max_length=8)


def configured() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())


def safe_inputs(run: dict) -> dict:
    # No arbitrary strings from providers, snapshots, reasoning, metadata, or dates.
    fields = (
        "score",
        "relative_20d",
        "relative_60d",
        "absolute_20d",
        "absolute_60d",
        "volatility_60d",
        "drawdown_60d",
    )
    from app.config import SECTOR_TICKERS

    return {
        "synthetic": run["mode"] == "demo",
        "available_sectors": run["coverage"]["available"],
        "expected_sectors": run["coverage"]["expected"],
        "ranks_available": run["ranking_status"] == "ranked",
        "sectors": [
            {"ticker": row["ticker"], **{key: float(row[key]) for key in fields}}
            for row in run["ranking"]
            if row["ticker"] in SECTOR_TICKERS
        ],
    }


def generate(run: dict) -> tuple[str, dict]:
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise ValueError("ai_not_configured")
    payload = safe_inputs(run)
    input_json = encode(payload)
    with httpx.Client(timeout=httpx.Timeout(45, connect=10)) as client:
        response = client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": 1800,
                "temperature": 0,
                "system": SYSTEM,
                "output_config": {
                    "format": {
                        "type": "json_schema",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "summary": {"type": "string"},
                                "observations": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "limitations": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": ["summary", "observations", "limitations"],
                            "additionalProperties": False,
                        },
                    }
                },
                "messages": [{"role": "user", "content": input_json}],
            },
        )
        response.raise_for_status()
        body = response.json()
    if body.get("stop_reason") != "end_turn":
        raise ValueError("incomplete_ai_response")
    raw = "".join(
        part["text"] for part in body.get("content", []) if part.get("type") == "text"
    )
    result = Explanation.model_validate(json.loads(raw)).model_dump()
    if re.search(r"\b(?:19|20)\d{2}\b|\b\d{4}-\d{2}-\d{2}\b", encode(result)):
        raise ValueError("unexpected_date_in_explanation")
    return hashlib.sha256(input_json.encode()).hexdigest(), result
