"""Transparent descriptive heuristic, not a forecast or investment recommendation."""

from datetime import date
from typing import Any

import pandas as pd

from app.config import CYCLE_SECTOR_MAP, SECTOR_NAMES, get_available_sectors


def cycle_context(macro: dict[str, pd.Series], end: date) -> dict:
    macro = {
        name: series.loc[series.index <= pd.Timestamp(end)]
        for name, series in macro.items()
    }
    unemployment = macro.get("UNEMPLOYMENT", pd.Series(dtype=float)).dropna()
    curve = macro.get("YIELD_CURVE", pd.Series(dtype=float)).dropna()
    if len(unemployment) < 4 or curve.empty:
        return {
            "phase": "unknown",
            "reason": "Requires four unemployment observations and a yield spread; cycle bonus disabled.",
        }
    if (pd.Timestamp(end) - unemployment.index[-1]).days > 75 or (
        pd.Timestamp(end) - curve.index[-1]
    ).days > 10:
        return {
            "phase": "unknown",
            "reason": "Macro inputs are stale; cycle bonus disabled.",
        }
    change = round(float(unemployment.iloc[-1] - unemployment.iloc[-4]), 6)
    spread = float(curve.iloc[-1])
    phase = (
        ("contraction" if change >= 0.3 else "slowdown")
        if spread < 0 or change >= 0.3
        else ("recovery" if change <= -0.2 else "expansion")
    )
    return {
        "phase": phase,
        "reason": f"Unemployment change over 3 observations: {change:+.2f} percentage points; 10Y−2Y spread: {spread:+.2f} points. Simple heuristic, not an official cycle designation.",
    }


def score_sectors(prices: pd.DataFrame, macro: dict[str, pd.Series], end: date) -> dict:
    prices = prices.loc[prices.index <= pd.Timestamp(end)]
    if "SPY" not in prices or len(prices["SPY"].dropna()) < 61:
        raise ValueError(
            "SPY requires at least 61 valid observations for benchmark analysis"
        )
    spy = prices["SPY"].dropna()
    if (pd.Timestamp(end) - spy.index[-1]).days > 7:
        raise ValueError("Benchmark prices are stale by more than 7 calendar days")
    window = spy.iloc[-61:]
    cycle = cycle_context(macro, end)
    rows: list[dict[str, Any]] = []
    excluded = dict(prices.attrs.get("unavailable", {}))
    for ticker in get_available_sectors(end):
        if ticker not in prices:
            excluded.setdefault(ticker, "No price data")
            continue
        values = prices[ticker].reindex(window.index)
        if values.isna().any() or (values <= 0).any():
            excluded[ticker] = (
                "Requires all 61 benchmark sessions; missing prices are not filled"
            )
            continue
        relative = []
        for horizon in (20, 60):
            sector_return = float(values.iloc[-1] / values.iloc[-horizon - 1] - 1)
            benchmark_return = float(window.iloc[-1] / window.iloc[-horizon - 1] - 1)
            relative.append(100 * (sector_return - benchmark_return))
        momentum = 0.4 * relative[0] + 0.6 * relative[1]
        bonus = 2.0 if ticker in CYCLE_SECTOR_MAP.get(cycle["phase"], []) else 0.0
        rows.append(
            {
                "ticker": ticker,
                "name": SECTOR_NAMES[ticker],
                "relative_20d": round(relative[0], 4),
                "relative_60d": round(relative[1], 4),
                "momentum_score": round(momentum, 4),
                "cycle_bonus": bonus,
                "score": round(momentum + bonus, 4),
                "last_price": round(float(values.iloc[-1]), 4),
            }
        )
    rows.sort(key=lambda row: (-row["score"], row["ticker"]))
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    return {
        "ranking": rows,
        "excluded": excluded,
        "cycle": cycle,
        "price_date": window.index[-1].date().isoformat(),
        "window_start": window.index[0].date().isoformat(),
        "methodology": "Score = 0.4 × 20-session excess return vs SPY + 0.6 × 60-session excess return vs SPY + 2 points for sectors in the cycle mapping. Returns are in percentage points; scores are not probabilities. All sectors use the same 61 benchmark sessions.",
    }
