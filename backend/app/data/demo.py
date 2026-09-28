"""Synthetic fixtures, explicitly selected; never substituted for live data."""

from datetime import date

import numpy as np
import pandas as pd

from app.config import get_available_sectors


def demo_prices(end: date) -> pd.DataFrame:
    dates = pd.bdate_range(end=pd.Timestamp(end), periods=100)
    t = np.arange(len(dates))
    tickers = [*get_available_sectors(end), "SPY"]
    return pd.DataFrame(
        {
            ticker: 100
            * np.exp((0.00015 + i * 0.00006) * t + 0.009 * np.sin(t / 9 + i))
            for i, ticker in enumerate(tickers)
        },
        index=dates,
    )


def demo_macro(end: date) -> dict[str, pd.Series]:
    dates = pd.date_range(end=pd.Timestamp(end), periods=6, freq="30D")
    return {
        "UNEMPLOYMENT": pd.Series([4.2, 4.2, 4.1, 4.1, 4.0, 4.0], index=dates),
        "YIELD_CURVE": pd.Series([0.1, 0.2, 0.3, 0.4, 0.5, 0.6], index=dates),
    }
