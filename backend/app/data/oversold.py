"""Oversold detector — finds price-vs-fundamentals divergences.

Compares price momentum against cycle alignment to flag sectors that are
technically oversold but fundamentally aligned with the current cycle phase.
Pure math — no LLM calls.
"""

import pandas as pd

from app.config import CYCLE_SECTOR_MAP, SECTOR_TICKERS


def detect_oversold(
    prices_df: pd.DataFrame,
    cycle_phase: str,
) -> list[dict]:
    """Detect oversold sectors.

    A sector is oversold when it has negative price momentum (both 1-month and
    3-month returns < 0) but is fundamentally aligned with the current cycle
    phase (alignment score > 60).

    Args:
        prices_df: DataFrame with columns = sector tickers, index = dates,
                   values = closing prices. Must have at least ~63 rows for
                   3-month lookback.
        cycle_phase: Current business cycle phase (e.g. "recovery").

    Returns:
        List of dicts with {ticker, price_return_1m, price_return_3m,
        cycle_alignment, is_oversold}.
    """
    favored = CYCLE_SECTOR_MAP.get(cycle_phase.lower(), [])
    results: list[dict] = []

    for ticker in prices_df.columns:
        if ticker not in SECTOR_TICKERS:
            continue

        col = prices_df[ticker].dropna()
        if len(col) < 2:
            continue

        # 1-month return (~21 trading days)
        lookback_1m = min(21, len(col) - 1)
        price_return_1m = (col.iloc[-1] / col.iloc[-1 - lookback_1m] - 1) * 100

        # 3-month return (~63 trading days)
        lookback_3m = min(63, len(col) - 1)
        price_return_3m = (col.iloc[-1] / col.iloc[-1 - lookback_3m] - 1) * 100

        # Cycle alignment score: 100 if in favored list, scaled by position
        # First in list = strongest alignment (100), last = weaker (60+)
        if ticker in favored:
            position = favored.index(ticker)
            # Score from 100 (first) down to ~65 (last), always > 60
            cycle_alignment = 100 - (position * (40 / max(len(favored) - 1, 1)))
        else:
            cycle_alignment = 0.0

        is_oversold = bool(
            price_return_1m < 0
            and price_return_3m < 0
            and cycle_alignment > 60
        )

        results.append(
            {
                "ticker": ticker,
                "price_return_1m": round(float(price_return_1m), 2),
                "price_return_3m": round(float(price_return_3m), 2),
                "cycle_alignment": round(float(cycle_alignment), 1),
                "is_oversold": is_oversold,
            }
        )

    return results
