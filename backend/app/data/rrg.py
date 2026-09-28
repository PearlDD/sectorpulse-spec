"""RRG (Relative Rotation Graph) quadrant classifier.

Implements JdK RS-Ratio and RS-Momentum using double-smoothed WMA.
Pure math — no LLM calls.
"""

import numpy as np
import pandas as pd


def wma(data: pd.Series, window: int = 10) -> pd.Series:
    """Weighted moving average where weights = [1, 2, ..., N]."""
    weights = np.arange(1, window + 1, dtype=float)

    def _apply(x: np.ndarray) -> float:
        return np.dot(x, weights) / weights.sum()

    return data.rolling(window).apply(_apply, raw=True)


def compute_rrg(
    prices_df: pd.DataFrame,
    benchmark: pd.Series,
    window: int = 10,
    trail_length: int = 5,
) -> dict:
    """Compute RRG data for all sectors.

    Args:
        prices_df: DataFrame with columns = sector tickers, index = dates,
                   values = closing prices.
        benchmark: Series of benchmark (SPY) closing prices, same index.
        window: WMA smoothing window (default 10).
        trail_length: Number of trailing data points for RRG chart animation.

    Returns:
        Dict mapping ticker -> {rs_ratio, rs_momentum, quadrant, trail}.
    """
    results: dict = {}

    for ticker in prices_df.columns:
        sector_prices = prices_df[ticker].dropna()

        # Align sector and benchmark on common dates
        common_idx = sector_prices.index.intersection(benchmark.index)
        if len(common_idx) < 2 * window + 1:
            continue
        sector = sector_prices.loc[common_idx]
        bench = benchmark.loc[common_idx]

        # Step 1: Relative Strength
        rs = (sector / bench) * 100

        # Step 2: Double-smoothed RS-Ratio
        rs_smooth = wma(rs, window)
        rs_benchmark = wma(rs_smooth, window)
        rs_ratio = (rs_smooth / rs_benchmark) * 100

        # Step 3: RS-Momentum (rate of change)
        rs_momentum = (rs_ratio / rs_ratio.shift(1)) * 100

        # Drop NaN rows
        valid = rs_ratio.dropna().index.intersection(rs_momentum.dropna().index)
        if len(valid) == 0:
            continue

        rs_ratio_valid = rs_ratio.loc[valid]
        rs_momentum_valid = rs_momentum.loc[valid]

        # Latest values
        latest_ratio = float(rs_ratio_valid.iloc[-1])
        latest_momentum = float(rs_momentum_valid.iloc[-1])

        # Quadrant classification
        quadrant = _classify_quadrant(latest_ratio, latest_momentum)

        # Trail: last N data points
        trail_start = max(0, len(rs_ratio_valid) - trail_length)
        trail = [
            {
                "rs_ratio": float(rs_ratio_valid.iloc[i]),
                "rs_momentum": float(rs_momentum_valid.iloc[i]),
            }
            for i in range(trail_start, len(rs_ratio_valid))
        ]

        results[ticker] = {
            "rs_ratio": latest_ratio,
            "rs_momentum": latest_momentum,
            "quadrant": quadrant,
            "trail": trail,
        }

    return results


def _classify_quadrant(rs_ratio: float, rs_momentum: float) -> str:
    """Classify into RRG quadrant based on RS-Ratio and RS-Momentum."""
    if rs_ratio > 100 and rs_momentum > 100:
        return "Leading"
    elif rs_ratio > 100 and rs_momentum < 100:
        return "Weakening"
    elif rs_ratio < 100 and rs_momentum < 100:
        return "Lagging"
    elif rs_ratio < 100 and rs_momentum > 100:
        return "Improving"
    else:
        # Edge case: exactly 100 on either axis
        return "Leading"
