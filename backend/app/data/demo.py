"""Synthetic fixtures, explicitly selected; never substituted for live data."""

from datetime import date

import numpy as np
import pandas as pd

from app.config import SECTOR_LAUNCH_DATES, SECTOR_TICKERS, get_available_sectors


def demo_prices(end: date) -> pd.DataFrame:
    dates = pd.bdate_range(end=pd.Timestamp(end), periods=1000)
    t = (dates - pd.Timestamp("1990-01-01")).days.to_numpy() / 7 * 5
    tickers = [*get_available_sectors(end), "SPY"]
    frame = pd.DataFrame(
        {
            ticker: 100
            * np.exp(
                (0.00003 + i * 0.000005) * t
                + 0.03 * np.sin(t / (17 + i) + i)
                + 0.02 * np.sin(t / 130 + i)
            )
            for ticker in tickers
            for i in [(SECTOR_TICKERS + ["SPY"]).index(ticker)]
        },
        index=dates,
    )
    for ticker in tickers:
        frame.loc[
            frame.index
            < pd.Timestamp(SECTOR_LAUNCH_DATES.get(ticker, date(1993, 1, 22))),
            ticker,
        ] = np.nan
    return frame


def demo_macro(end: date) -> dict[str, pd.Series]:
    dates = pd.date_range(end=pd.Timestamp(end), periods=6, freq="30D")
    return {
        "UNEMPLOYMENT": pd.Series([4.2, 4.2, 4.1, 4.1, 4.0, 4.0], index=dates),
        "YIELD_CURVE": pd.Series([0.1, 0.2, 0.3, 0.4, 0.5, 0.6], index=dates),
    }
