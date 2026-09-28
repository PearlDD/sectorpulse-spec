"""Versioned descriptive calculations: no macro bonus and no LLM dependency."""

from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from app.config import SECTOR_NAMES, get_available_sectors
from app.data.snapshot import MAX_AGE, clean

METHOD_VERSION = "relative-strength-v2"
MIN_COVERAGE = 0.8


def macro_context(macro: dict[str, pd.Series], end: date) -> list[dict]:
    def usable(name):
        values = clean(macro.get(name, pd.Series(dtype=float)), end)
        if values.empty or (pd.Timestamp(end) - values.index[-1]).days > MAX_AGE[name]:
            return pd.Series(dtype=float)
        return values

    unemployment, cpi = usable("UNEMPLOYMENT"), usable("CPI")
    curve, spread, vix = usable("YIELD_CURVE"), usable("HY_SPREAD"), usable("VIX")
    growth: dict[str, Any] = {
        "name": "Labor trend",
        "state": "unavailable",
        "evidence": "Need four fresh unemployment observations.",
    }
    if len(unemployment) >= 4:
        delta = round(float(unemployment.iloc[-1] - unemployment.iloc[-4]), 4)
        growth.update(
            state="softening"
            if delta >= 0.3
            else "improving"
            if delta <= -0.2
            else "mixed",
            evidence=f"Unemployment change across three observation intervals: {delta:+.2f} pp. This is one labor-market proxy, not a cycle designation.",
        )
    inflation: dict[str, Any] = {
        "name": "Inflation",
        "state": "unavailable",
        "evidence": "Need fourteen fresh monthly CPI observations to compare year-on-year rates.",
    }
    if len(cpi) >= 14 and cpi.iloc[-13] > 0 and cpi.iloc[-14] > 0:
        latest = 100 * (cpi.iloc[-1] / cpi.iloc[-13] - 1)
        previous = 100 * (cpi.iloc[-2] / cpi.iloc[-14] - 1)
        inflation.update(
            state="accelerating"
            if latest > previous + 0.1
            else "easing"
            if latest < previous - 0.1
            else "mixed",
            evidence=f"CPI year-on-year: {latest:.2f}%; previous observation: {previous:.2f}%.",
        )
    stress: dict[str, Any] = {
        "name": "Market stress",
        "state": "unavailable",
        "evidence": "Need both fresh high-yield spread and VIX inputs.",
    }
    if not spread.empty and not vix.empty:
        high = spread.iloc[-1] >= 5 or vix.iloc[-1] >= 25
        stress.update(
            state="elevated" if high else "not elevated",
            evidence=f"HY spread {spread.iloc[-1]:.2f}%; VIX {vix.iloc[-1]:.2f}. Descriptive thresholds: 5% or 25; not calibrated probabilities.",
        )
    rates = {
        "name": "Yield curve",
        "state": "unavailable",
        "evidence": "Need a fresh 10Y−2Y spread.",
    }
    if not curve.empty:
        rates.update(
            state="inverted" if curve.iloc[-1] < 0 else "not inverted",
            evidence=f"10Y−2Y: {curve.iloc[-1]:+.2f} pp. Does not alone determine the business cycle.",
        )
    return [growth, inflation, stress, rates]


def relative_map(values: pd.Series, spy: pd.Series) -> dict:
    """Public formula, NOT a proprietary JdK RRG reproduction."""
    relative = values / spy
    strength = 100 * (relative / relative.shift(20) - 1)
    momentum = strength - strength.shift(5)
    valid = pd.DataFrame({"strength": strength, "momentum": momentum}).dropna().tail(6)
    trail: list[dict[str, Any]] = [
        {
            "date": pd.Timestamp(str(day)).date().isoformat(),
            "strength": round(float(row["strength"]), 4),
            "momentum": round(float(row["momentum"]), 4),
        }
        for day, row in valid.iterrows()
    ]
    latest = trail[-1]
    x, y = latest["strength"], latest["momentum"]
    quadrant = (
        "leading / accelerating"
        if x >= 0 and y >= 0
        else "leading / slowing"
        if x >= 0
        else "lagging / improving"
        if y >= 0
        else "lagging / weakening"
    )
    return {"trail": trail, "quadrant": quadrant, **latest}


def score_sectors(prices: pd.DataFrame, macro: dict[str, pd.Series], end: date) -> dict:
    prices = prices.loc[prices.index <= pd.Timestamp(end)].replace(
        [np.inf, -np.inf], np.nan
    )
    if "SPY" not in prices or len(prices["SPY"].dropna()) < 61:
        raise ValueError(
            "SPY requires at least 61 valid observations for benchmark analysis"
        )
    spy = prices["SPY"].dropna()
    if (spy <= 0).any():
        raise ValueError("Benchmark prices must be positive")
    if (pd.Timestamp(end) - spy.index[-1]).days > 7:
        raise ValueError("Benchmark prices are stale by more than 7 calendar days")
    window = spy.iloc[-61:]
    rows: list[dict[str, Any]] = []
    excluded = dict(prices.attrs.get("unavailable", {}))
    universe = get_available_sectors(end)
    rotation = {}
    for ticker in universe:
        if ticker not in prices:
            excluded.setdefault(ticker, "No price data")
            continue
        values = prices[ticker].reindex(window.index)
        if values.isna().any() or (values <= 0).any():
            missing = int((values.isna() | (values <= 0)).sum())
            excluded[ticker] = (
                f"{missing} invalid/missing observations in 61 benchmark sessions; no filling"
            )
            continue
        row: dict[str, Any] = {
            "ticker": ticker,
            "name": SECTOR_NAMES[ticker],
            "last_price": round(float(values.iloc[-1]), 4),
        }
        for horizon in (20, 60):
            absolute = 100 * float(values.iloc[-1] / values.iloc[-horizon - 1] - 1)
            benchmark = 100 * float(window.iloc[-1] / window.iloc[-horizon - 1] - 1)
            row[f"absolute_{horizon}d"] = round(absolute, 4)
            row[f"relative_{horizon}d"] = round(absolute - benchmark, 4)
        returns = values.pct_change(fill_method=None).dropna()
        row.update(
            score=round(0.4 * row["relative_20d"] + 0.6 * row["relative_60d"], 4),
            volatility_60d=round(float(returns.std(ddof=1) * np.sqrt(252) * 100), 4),
            drawdown_60d=round(float((values / values.cummax() - 1).min() * 100), 4),
        )
        rows.append(row)
        rotation[ticker] = relative_map(values, window)
    if not rows:
        raise ValueError("No sectors have a complete valid comparison window")
    enough = len(rows) / len(universe) >= MIN_COVERAGE
    rows.sort(key=lambda row: (-row["score"], row["ticker"]))
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank if enough else None
    return {
        "ranking": rows,
        "excluded": excluded,
        "context": macro_context(macro, end),
        "method_version": METHOD_VERSION,
        "rotation": rotation,
        "ranking_status": "ranked" if enough else "insufficient_coverage",
        "coverage": {
            "available": len(rows),
            "expected": len(universe),
            "minimum_fraction": MIN_COVERAGE,
        },
        "price_date": window.index[-1].date().isoformat(),
        "window_start": window.index[0].date().isoformat(),
        "methodology": "Descriptive strength = 0.4 × 20-session excess return + 0.6 × 60-session excess return vs SPY (percentage points). No macro bonus. Volatility is annualized from 60 daily returns; drawdown uses the same window. Ordinal ranks require at least 80% of eligible sectors. Weights are fixed and not claimed optimal.",
        "rotation_method": "X = 20-session return of sector/SPY price ratio (%); Y = change in X over 5 sessions (pp). Six observed-session trail points. Custom relative-strength map, not JdK RRG or a forecast.",
    }
